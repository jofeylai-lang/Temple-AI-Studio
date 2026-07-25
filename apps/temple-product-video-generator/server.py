from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
import zipfile
from datetime import datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from PIL import Image, ImageDraw, ImageFont


APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from temple_ai_studio.script_engine import generate_video_script_package
from temple_ai_studio.image_pipeline import run_image_pipeline
from temple_ai_studio.emma_core import EmmaCore
from temple_ai_studio.temple_os import TempleOSKernel
from temple_ai_studio.video_intelligence import run_video_generation_pipeline
from temple_ai_studio.production_workflow import (
    ProductionWorkflowBlocked,
    RealProductionWorkflow,
)

DATA_ROOT = Path(os.environ.get("TPVG_DATA_DIR", APP_ROOT / "data")).resolve()
DB_PATH = DATA_ROOT / "database.json"
CONFIG_PATH = DATA_ROOT / "config.json"
UPLOAD_ROOT = DATA_ROOT / "uploads"
PROJECT_ROOT = DATA_ROOT / "projects"
EXPORT_ROOT = DATA_ROOT / "exports"
RUNTIME_ROOT = APP_ROOT / "runtime"
BACKUP_ROOT = DATA_ROOT / "backups"
EVIDENCE_ROOT = DATA_ROOT / "evidence"
LOG_ROOT = DATA_ROOT / "logs"
SUPPORT_ROOT = DATA_ROOT / "support"
RELEASE_ROOT = APP_ROOT / "release"
VERSION = "1.1.1"
CURRENT_SCHEMA_VERSION = 2

VIDEO_STATES = [
    "Draft",
    "Planning",
    "Generating",
    "Partially Failed",
    "Ready for Preview",
    "Approved",
    "Exporting",
    "Completed",
]

DB_LOCK = threading.Lock()
JOB_THREAD_LOCK = threading.Lock()
ACTIVE_JOB_THREADS: dict[str, threading.Thread] = {}
DATABASE_RECOVERY_STATE = {
    "recovered": False,
    "message": "",
    "backupPath": "",
}

JOB_STAGES = [
    {"key": "validation", "label": "驗證需求", "progress": 3},
    {"key": "product", "label": "載入商品資料", "progress": 8},
    {"key": "research", "label": "整理需求與知識", "progress": 14},
    {"key": "script", "label": "生成腳本", "progress": 22},
    {"key": "storyboard", "label": "規劃分鏡", "progress": 32},
    {"key": "images", "label": "處理影像", "progress": 44},
    {"key": "emma", "label": "檢查 Emma 一致性", "progress": 54},
    {"key": "video", "label": "生成影片", "progress": 66},
    {"key": "audio", "label": "處理聲音", "progress": 74},
    {"key": "subtitles", "label": "建立字幕", "progress": 82},
    {"key": "editing", "label": "自動剪輯", "progress": 89},
    {"key": "render", "label": "渲染影片", "progress": 96},
    {"key": "export", "label": "完成輸出", "progress": 100},
]


def production_data_root() -> Path:
    return Path(
        os.environ.get(
            "TEMPLE_PRODUCTION_DATA_ROOT",
            REPO_ROOT.parent / "Temple AI Studio Production Data",
        )
    ).resolve()


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"


def safe_name(value: str, fallback: str = "item") -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", value or "").strip(" .")
    value = re.sub(r"\s+", "-", value)
    return value[:90] or fallback


def ensure_dirs() -> None:
    for path in [DATA_ROOT, UPLOAD_ROOT, PROJECT_ROOT, EXPORT_ROOT, RUNTIME_ROOT, BACKUP_ROOT, EVIDENCE_ROOT, LOG_ROOT, SUPPORT_ROOT, RELEASE_ROOT]:
        path.mkdir(parents=True, exist_ok=True)


def append_log(name: str, message: str, payload: dict | None = None) -> None:
    ensure_dirs()
    record = {"time": now_iso(), "message": message}
    if payload:
        record["details"] = payload
    with (LOG_ROOT / name).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def default_config() -> dict:
    ffmpeg = detect_ffmpeg()
    return {
        "comfyuiUrl": "http://127.0.0.1:8188",
        "comfyuiWorkflow": "",
        "ffmpegPath": ffmpeg or "",
        "whisperPath": "",
        "ttsProvider": "none",
        "outputDir": str(EXPORT_ROOT),
        "defaultDuration": 30,
        "includeLogo": True,
        "subtitleStyle": "安全區底部白字深色陰影",
        "providerMode": "local-first",
        "cloudEnabled": False,
        "version": VERSION,
        "createdAt": now_iso(),
        "updatedAt": now_iso(),
    }


def empty_db() -> dict:
    return {
        "schemaVersion": CURRENT_SCHEMA_VERSION,
        "dataVersion": "2.0",
        "products": [],
        "projects": [],
        "jobs": [],
        "errors": [],
        "createdAt": now_iso(),
        "updatedAt": now_iso(),
    }


def load_config() -> dict:
    ensure_dirs()
    if not CONFIG_PATH.exists():
        atomic_write_json(CONFIG_PATH, default_config())
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if config.get("version") != VERSION:
        config["version"] = VERSION
        config["updatedAt"] = now_iso()
        atomic_write_json(CONFIG_PATH, config)
    return config


def save_config(config: dict) -> dict:
    current = load_config()
    allowed = {
        "comfyuiUrl",
        "comfyuiWorkflow",
        "ffmpegPath",
        "whisperPath",
        "ttsProvider",
        "outputDir",
        "defaultDuration",
        "includeLogo",
        "subtitleStyle",
        "providerMode",
        "cloudEnabled",
    }
    for key in allowed:
        if key in config:
            current[key] = config[key]
    current["defaultDuration"] = int(current.get("defaultDuration") or 30)
    current["includeLogo"] = str(current.get("includeLogo", "true")).lower() == "true"
    current["cloudEnabled"] = False
    current["version"] = VERSION
    current["updatedAt"] = now_iso()
    atomic_write_json(CONFIG_PATH, current)
    return current


def load_db() -> dict:
    ensure_dirs()
    if not DB_PATH.exists():
        atomic_write_json(DB_PATH, empty_db())
    try:
        db = json.loads(DB_PATH.read_text(encoding="utf-8"))
        if not isinstance(db, dict):
            raise ValueError("資料庫根節點必須是物件")
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as error:
        corrupt_dir = BACKUP_ROOT / "corrupt-database"
        corrupt_dir.mkdir(parents=True, exist_ok=True)
        backup_path = corrupt_dir / f"database-corrupt-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        shutil.copy2(DB_PATH, backup_path)
        db = empty_db()
        atomic_write_json(DB_PATH, db)
        DATABASE_RECOVERY_STATE.update(
            {
                "recovered": True,
                "message": f"已隔離損毀資料庫並建立可用空資料庫：{error}",
                "backupPath": str(backup_path),
            }
        )
        append_log(
            "recovery.log",
            "database-corruption-recovered",
            {"error": str(error), "backupPath": str(backup_path)},
        )
    db = migrate_db(db)
    db.setdefault("products", [])
    db.setdefault("projects", [])
    db.setdefault("jobs", [])
    db.setdefault("errors", [])
    return db


def migrate_db(db: dict) -> dict:
    version = int(db.get("schemaVersion", 0) or 0)
    if version > CURRENT_SCHEMA_VERSION:
        raise ValueError("資料版本高於目前程式可支援版本，請先備份並使用相容版本。")
    if version < CURRENT_SCHEMA_VERSION:
        migration_dir = BACKUP_ROOT / "migrations"
        migration_dir.mkdir(parents=True, exist_ok=True)
        backup_path = migration_dir / f"database-before-schema-{CURRENT_SCHEMA_VERSION}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        backup_path.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
        db.setdefault("jobs", [])
        db["schemaVersion"] = CURRENT_SCHEMA_VERSION
        db["dataVersion"] = "2.0"
        db["migratedAt"] = now_iso()
        atomic_write_json(DB_PATH, db)
        append_log("recovery.log", "database-migrated", {"from": version, "to": CURRENT_SCHEMA_VERSION, "backup": str(backup_path)})
    return db


def save_db(db: dict) -> None:
    db["updatedAt"] = now_iso()
    atomic_write_json(DB_PATH, db)


def database_health() -> dict:
    ensure_dirs()
    schema_version = None
    product_count = 0
    job_count = 0
    migration_status = "尚未初始化"
    error_message = ""
    try:
        db = load_db()
        schema_version = db.get("schemaVersion")
        product_count = len(db.get("products", []))
        job_count = len(db.get("jobs", []))
        migration_status = (
            "已復原損毀資料庫"
            if DATABASE_RECOVERY_STATE["recovered"]
            else "已是最新版本"
        )
    except Exception as error:
        error_message = str(error)
        migration_status = "資料庫無法使用"
    exists = DB_PATH.exists()
    readable = exists and os.access(DB_PATH, os.R_OK)
    writable = os.access(DB_PATH if exists else DB_PATH.parent, os.W_OK)
    return {
        "path": str(DB_PATH),
        "exists": exists,
        "readable": readable,
        "writable": writable,
        "schemaVersion": schema_version,
        "targetSchemaVersion": CURRENT_SCHEMA_VERSION,
        "migrationStatus": migration_status,
        "productCount": product_count,
        "jobCount": job_count,
        "apiHealth": "正常" if not error_message else "異常",
        "error": error_message,
        "recovery": dict(DATABASE_RECOVERY_STATE),
    }


def detect_ffmpeg() -> str:
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    candidates = [
        shutil.which("ffmpeg"),
        str(
            local
            / "Comfy-Desktop"
            / "ComfyUI-Installs"
            / "ComfyUI"
            / "ComfyUI"
            / ".venv"
            / "Lib"
            / "site-packages"
            / "imageio_ffmpeg"
            / "binaries"
            / "ffmpeg-win-x86_64-v7.1.exe"
        ),
        r"C:\Program Files\Softdeluxe\Free Download Manager\ffmpeg.exe",
        str(APP_ROOT / "bin" / "ffmpeg.exe"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate).resolve())
    return ""


def ffmpeg_version(ffmpeg_path: str) -> str:
    if not ffmpeg_path or not Path(ffmpeg_path).exists():
        return ""
    try:
        result = subprocess.run(
            [ffmpeg_path, "-version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
        )
        return result.stdout.splitlines()[0] if result.stdout else ""
    except Exception:
        return ""


def comfyui_health(url: str) -> dict:
    try:
        import urllib.request

        with urllib.request.urlopen(url.rstrip("/") + "/system_stats", timeout=1.5) as response:
            return {"connected": response.status == 200, "message": "ComfyUI 已連線"}
    except Exception as error:
        return {"connected": False, "message": f"ComfyUI 尚未連線：{error.__class__.__name__}"}


def temple_os_status() -> dict:
    try:
        return TempleOSKernel(REPO_ROOT).status()
    except Exception as error:
        return {
            "status": "degraded",
            "message": str(error),
            "errorType": error.__class__.__name__,
        }


def health_payload() -> dict:
    config = load_config()
    ffmpeg = config.get("ffmpegPath") or detect_ffmpeg()
    production_root = production_data_root()
    try:
        production_activation = RealProductionWorkflow(
            REPO_ROOT,
            production_root,
        ).preflight(run_health=False)
    except Exception as error:
        production_activation = {
            "overall": "BLOCKED",
            "blockers": [
                {
                    "code": "production-activation-error",
                    "message": str(error),
                }
            ],
        }
    return {
        "status": "ok",
        "time": now_iso(),
        "dataRoot": str(DATA_ROOT),
        "logRoot": str(LOG_ROOT),
        "database": database_health(),
        "ffmpeg": {
            "path": ffmpeg,
            "available": bool(ffmpeg and Path(ffmpeg).exists()),
            "version": ffmpeg_version(ffmpeg),
        },
        "version": VERSION,
        "comfyui": comfyui_health(config.get("comfyuiUrl", "")),
        "whisper": {
            "path": config.get("whisperPath", ""),
            "available": bool(config.get("whisperPath") and Path(config["whisperPath"]).exists()),
        },
        "tts": {
            "provider": config.get("ttsProvider", "none"),
            "available": config.get("ttsProvider") not in ["", "none"],
        },
        "emmaCore": EmmaCore(production_root).status(),
        "templeOS": temple_os_status(),
        "productionActivation": production_activation,
    }


def get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_paths = [
        r"C:\Windows\Fonts\msjh.ttc",
        r"C:\Windows\Fonts\mingliu.ttc",
        r"C:\Windows\Fonts\arial.ttf",
    ]
    for path in font_paths:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    lines: list[str] = []
    for raw in str(text).splitlines() or [""]:
        current = ""
        for char in raw:
            test = current + char
            if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = char
        if current:
            lines.append(current)
    return lines[:6]


def make_demo_image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1200, 1600), "#f6efe6")
    draw = ImageDraw.Draw(img)
    title_font = get_font(72)
    text_font = get_font(34)
    draw.rounded_rectangle((360, 330, 840, 1120), radius=42, fill="#2f6f61")
    draw.rounded_rectangle((430, 220, 770, 380), radius=70, fill="#d9b36c")
    draw.ellipse((470, 450, 730, 710), fill="#f2d18a")
    draw.rectangle((500, 690, 700, 980), fill="#e8c46f")
    draw.text((250, 1240), "Temple Energy Candle", fill="#17231f", font=title_font)
    draw.text((315, 1340), "示範商品照片", fill="#65513a", font=text_font)
    img.save(path)


def image_url(path: str) -> str:
    rel = Path(path).resolve().relative_to(DATA_ROOT)
    return "/api/files/" + rel.as_posix()


def seed_demo_data() -> dict:
    with DB_LOCK:
        db = load_db()
        if db["products"]:
            return db
        product_id = "product-demo-candle"
        img_path = UPLOAD_ROOT / product_id / "demo-temple-candle.png"
        make_demo_image(img_path)
        db["products"].append(
            {
                "id": product_id,
                "name": "Temple Energy Candle",
                "category": "能量蠟燭",
                "description": "以日常靜心與空間儀式為核心的手作蠟燭。",
                "sellingPoint": "讓使用者在忙碌生活裡建立一個穩定、安靜、可重複的儀式時刻。",
                "spiritualInfo": "適合冥想、睡前整理心緒、日常祝福與空間淨化感的情境。",
                "targetAudience": "喜歡質感生活、身心靈日常與送禮儀式感的使用者。",
                "materials": [
                    {
                        "id": "material-demo-candle",
                        "fileName": "demo-temple-candle.png",
                        "mime": "image/png",
                        "path": str(img_path),
                        "url": image_url(str(img_path)),
                        "role": "主商品照片",
                        "order": 1,
                        "createdAt": now_iso(),
                    }
                ],
                "createdAt": now_iso(),
                "updatedAt": now_iso(),
            }
        )
        save_db(db)
        return db


def validate_product(product: dict) -> list[str]:
    errors = []
    required = {
        "name": "商品名稱",
        "category": "商品類型",
        "description": "商品說明",
        "sellingPoint": "商品特色",
    }
    for key, label in required.items():
        if not str(product.get(key, "")).strip():
            errors.append(f"{label}不可空白")
    return errors


def create_product(payload: dict) -> dict:
    product = {
        "id": new_id("product"),
        "name": str(payload.get("name", "")).strip(),
        "category": str(payload.get("category", "")).strip(),
        "description": str(payload.get("description", "")).strip(),
        "sellingPoint": str(payload.get("sellingPoint", "")).strip(),
        "productInfo": str(payload.get("productInfo", "")).strip(),
        "spiritualInfo": str(payload.get("spiritualInfo", "")).strip(),
        "targetAudience": str(payload.get("targetAudience", "")).strip(),
        "tags": split_terms(payload.get("tags", "")),
        "seoKeywords": split_terms(payload.get("seoKeywords", "")),
        "materials": [],
        "createdAt": now_iso(),
        "updatedAt": now_iso(),
    }
    errors = validate_product(product)
    if errors:
        raise ValueError("；".join(errors))
    with DB_LOCK:
        db = load_db()
        db["products"].append(product)
        save_db(db)
    return product


def update_product(product_id: str, payload: dict) -> dict:
    with DB_LOCK:
        db = load_db()
        product = find_item(db["products"], product_id)
        for key in [
            "name",
            "category",
            "description",
            "sellingPoint",
            "productInfo",
            "spiritualInfo",
            "targetAudience",
        ]:
            if key in payload:
                product[key] = str(payload.get(key, "")).strip()
        for key in ["tags", "seoKeywords"]:
            if key in payload:
                product[key] = split_terms(payload.get(key, ""))
        errors = validate_product(product)
        if errors:
            raise ValueError("；".join(errors))
        product["updatedAt"] = now_iso()
        save_db(db)
        return product


def delete_product(product_id: str) -> dict:
    with DB_LOCK:
        db = load_db()
        before = len(db["products"])
        db["products"] = [item for item in db["products"] if item["id"] != product_id]
        if len(db["products"]) == before:
            raise KeyError("找不到商品")
        save_db(db)
    return {"deleted": product_id}


def split_terms(value) -> list[str]:
    if isinstance(value, list):
        terms = value
    else:
        terms = re.split(r"[,，、\n]+", str(value or ""))
    return list(dict.fromkeys(term.strip() for term in terms if term.strip()))


def material_kind(file_name: str, requested: str = "") -> str:
    if requested in {"image", "logo", "video", "document"}:
        return requested
    suffix = Path(file_name).suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
        return "image"
    if suffix in {".mp4", ".mov", ".webm"}:
        return "video"
    return "document"


def add_materials(product_id: str, files: list[dict], requested_kind: str = "") -> dict:
    if not files:
        raise ValueError("請至少選擇一個商品素材")
    saved = []
    with DB_LOCK:
        db = load_db()
        product = find_item(db["products"], product_id)
        target_dir = UPLOAD_ROOT / product_id
        target_dir.mkdir(parents=True, exist_ok=True)
        next_order = len(product.get("materials", [])) + 1
        for item in files:
            raw_name = safe_name(item.get("name", "product-image.png"), "product-image.png")
            data_url = item.get("data", "")
            if "," in data_url:
                data_url = data_url.split(",", 1)[1]
            blob = base64.b64decode(data_url)
            if len(blob) > 25 * 1024 * 1024:
                raise ValueError("單一素材不可超過 25MB")
            suffix = Path(raw_name).suffix.lower()
            allowed = {
                ".png",
                ".jpg",
                ".jpeg",
                ".webp",
                ".bmp",
                ".mp4",
                ".mov",
                ".webm",
                ".pdf",
                ".txt",
                ".docx",
            }
            if suffix not in allowed:
                raise ValueError("不支援此素材格式")
            material_id = new_id("material")
            path = target_dir / f"{material_id}{suffix}"
            path.write_bytes(blob)
            kind = material_kind(raw_name, item.get("kind") or requested_kind)
            width = 0
            height = 0
            if kind in {"image", "logo"}:
                with Image.open(path) as img:
                    width, height = img.size
                    img.verify()
            digest = hashlib.sha256(blob).hexdigest()
            if any(existing.get("sha256") == digest for existing in product.get("materials", [])):
                path.unlink(missing_ok=True)
                continue
            material = {
                "id": material_id,
                "fileName": raw_name,
                "mime": item.get("type", "image/*"),
                "kind": kind,
                "path": str(path),
                "url": image_url(str(path)),
                "role": (
                    "品牌 Logo"
                    if kind == "logo"
                    else "商品影片"
                    if kind == "video"
                    else "商品文件"
                    if kind == "document"
                    else "商品照片"
                    if next_order > 1
                    else "主商品照片"
                ),
                "order": next_order,
                "width": width,
                "height": height,
                "sha256": digest,
                "createdAt": now_iso(),
            }
            product.setdefault("materials", []).append(material)
            saved.append(material)
            next_order += 1
        product["updatedAt"] = now_iso()
        save_db(db)
    if not saved:
        raise ValueError("所選素材與既有檔案重複，未再次加入。")
    return {"materials": saved}


def replace_material(product_id: str, material_id: str, file_payload: dict) -> dict:
    with DB_LOCK:
        db = load_db()
        product = find_item(db["products"], product_id)
        material = find_item(product.get("materials", []), material_id)
        data_url = file_payload.get("data", "")
        if "," in data_url:
            data_url = data_url.split(",", 1)[1]
        blob = base64.b64decode(data_url)
        suffix = Path(safe_name(file_payload.get("name", "replacement.png"))).suffix.lower()
        if suffix not in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]:
            raise ValueError("僅支援 PNG、JPG、WEBP、BMP 圖片")
        target_dir = UPLOAD_ROOT / product_id
        target_dir.mkdir(parents=True, exist_ok=True)
        new_path = target_dir / f"{material_id}-replacement-{uuid.uuid4().hex[:6]}{suffix}"
        new_path.write_bytes(blob)
        with Image.open(new_path) as img:
            width, height = img.size
            img.verify()
        material["previousPath"] = material.get("path")
        material["fileName"] = safe_name(file_payload.get("name", "replacement.png"))
        material["mime"] = file_payload.get("type", "image/*")
        material["path"] = str(new_path)
        material["url"] = image_url(str(new_path))
        material["width"] = width
        material["height"] = height
        material["updatedAt"] = now_iso()
        product["updatedAt"] = now_iso()
        save_db(db)
        return material


def move_material(product_id: str, material_id: str, direction: str) -> dict:
    with DB_LOCK:
        db = load_db()
        product = find_item(db["products"], product_id)
        materials = sorted(product.get("materials", []), key=lambda item: item.get("order", 0))
        index = next((i for i, item in enumerate(materials) if item["id"] == material_id), -1)
        if index < 0:
            raise KeyError("找不到照片")
        swap = index - 1 if direction == "up" else index + 1
        if 0 <= swap < len(materials):
            materials[index], materials[swap] = materials[swap], materials[index]
        for order, item in enumerate(materials, start=1):
            item["order"] = order
            if item.get("kind", "image") == "image":
                item["role"] = "主商品照片" if order == 1 else "商品照片"
        product["materials"] = materials
        product["updatedAt"] = now_iso()
        save_db(db)
        return {"materials": materials}


def delete_material(product_id: str, material_id: str) -> dict:
    with DB_LOCK:
        db = load_db()
        product = find_item(db["products"], product_id)
        material = find_item(product.get("materials", []), material_id)
        product["materials"] = [item for item in product.get("materials", []) if item["id"] != material_id]
        product["updatedAt"] = now_iso()
        save_db(db)
    return {"deleted": material_id, "keptOriginalPath": material.get("path")}


def find_item(items: list[dict], item_id: str) -> dict:
    for item in items:
        if item.get("id") == item_id:
            return item
    raise KeyError("找不到資料")


def generate_content(product: dict, payload: dict, project_id: str) -> dict:
    return generate_video_script_package(product, payload, project_id)


def duration_conflict(payload: dict) -> dict | None:
    requirement = str(payload.get("requirement", ""))
    selected = int(payload.get("duration") or load_config().get("defaultDuration") or 30)
    matches = re.findall(r"(?<!\d)(\d{1,3})\s*(?:秒鐘|秒|seconds?|secs?|s)", requirement, re.IGNORECASE)
    if not matches:
        return None
    requested = int(matches[-1])
    if requested == selected:
        return None
    return {
        "selectedDuration": selected,
        "requestDuration": requested,
        "message": f"文字需求提到 {requested} 秒，但介面選擇 {selected} 秒；本次以介面設定為準。",
    }


def validate_project_submission(payload: dict) -> dict:
    mode = str(payload.get("mode", "product")).strip().lower()
    if mode not in {"product", "text-only"}:
        mode = "product"
    errors: dict[str, str] = {}
    requirement = str(payload.get("requirement", "")).strip()
    if not requirement:
        errors["requirement"] = "請輸入中文影片需求。"
    try:
        duration = int(payload.get("duration") or load_config().get("defaultDuration") or 30)
    except (TypeError, ValueError):
        duration = 0
    if duration < 5 or duration > 180:
        errors["duration"] = "影片秒數必須介於 5 到 180 秒。"

    product = None
    if mode == "product":
        product_id = str(payload.get("productId", "")).strip()
        if not product_id:
            errors["productId"] = "請選擇商品，或改用純文字模式。"
        else:
            try:
                product = find_item(load_db()["products"], product_id)
            except KeyError:
                errors["productId"] = "找不到所選商品，請重新整理或建立商品。"
        if product and not any(item.get("kind", "image") in {"image", "logo"} for item in product.get("materials", [])):
            errors["materials"] = "商品影片至少需要一張商品照片或 Logo。"
    if errors:
        error = ValueError("；".join(errors.values()))
        error.field_errors = errors
        raise error
    return {
        "mode": mode,
        "duration": duration,
        "requirement": requirement,
        "product": product,
        "durationConflict": duration_conflict({**payload, "duration": duration}),
    }


def inline_product(payload: dict) -> dict:
    requirement = str(payload.get("requirement", "")).strip()
    return {
        "id": "",
        "name": str(payload.get("textProjectName", "")).strip() or "純文字影片",
        "category": "純文字內容",
        "description": requirement,
        "sellingPoint": requirement,
        "productInfo": "",
        "spiritualInfo": str(payload.get("spiritualInfo", "")).strip(),
        "targetAudience": str(payload.get("targetAudience", "")).strip(),
        "tags": [],
        "seoKeywords": [],
        "materials": [],
    }


def create_project_record(payload: dict, validation: dict | None = None) -> dict:
    validation = validation or validate_project_submission(payload)
    mode = validation["mode"]
    product = validation.get("product") or inline_product(payload)
    project_id = new_id("project")
    content_payload = {
        **payload,
        "duration": validation["duration"],
        "requirement": validation["requirement"],
    }
    content = generate_content(product, content_payload, project_id)
    with DB_LOCK:
        db = load_db()
        configured_output = Path(load_config().get("outputDir") or EXPORT_ROOT).resolve()
        project_dir = PROJECT_ROOT / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        project = {
            "id": project_id,
            "productId": product.get("id", ""),
            "productName": product["name"],
            "mode": mode,
            "inlineProduct": product if mode == "text-only" else None,
            "status": "Planning",
            "reviewStatus": "未審核",
            "createdAt": now_iso(),
            "updatedAt": now_iso(),
            "outputDir": str(configured_output / project_id),
            "projectDir": str(project_dir),
            "renderHistory": [],
            "errors": [],
            "durationConflict": validation.get("durationConflict"),
            **content,
        }
        db["projects"].append(project)
        save_db(db)
    append_log(
        "generation.log",
        "project-created",
        {
            "projectId": project_id,
            "productId": product.get("id", ""),
            "mode": mode,
            "platform": project["platform"],
            "durationConflict": validation.get("durationConflict"),
        },
    )
    return project


def create_project(payload: dict) -> dict:
    project = create_project_record(payload)
    return render_project(project["id"], preview=True)


def resolve_project_product(db: dict, project: dict) -> dict:
    if project.get("mode") == "text-only" or not project.get("productId"):
        return project.get("inlineProduct") or inline_product(project)
    return find_item(db["products"], project["productId"])


def update_scene(project_id: str, scene_id: str, payload: dict) -> dict:
    with DB_LOCK:
        db = load_db()
        project = find_item(db["projects"], project_id)
        scene = find_item(project["scenes"], scene_id)
        for key in ["visualDescription", "narration", "subtitle", "prompt"]:
            if key in payload:
                scene[key] = str(payload[key]).strip()
        scene["updatedAt"] = now_iso()
        project["updatedAt"] = now_iso()
        project["status"] = "Ready for Preview"
        save_db(db)
        return project


def approve_scene(project_id: str, scene_id: str) -> dict:
    with DB_LOCK:
        db = load_db()
        project = find_item(db["projects"], project_id)
        scene = find_item(project["scenes"], scene_id)
        scene["approved"] = True
        scene["status"] = "Approved"
        scene["updatedAt"] = now_iso()
        project["updatedAt"] = now_iso()
        save_db(db)
        return project


def regenerate_scene(project_id: str, scene_id: str, progress_callback=None) -> dict:
    with DB_LOCK:
        db = load_db()
        project = find_item(db["projects"], project_id)
        scene = find_item(project["scenes"], scene_id)
        if scene.get("approved"):
            raise ValueError("此場景已批准。若要重生，請先取消批准或編輯文字。")
        scene["version"] += 1
        scene["status"] = "Ready for Preview"
        scene["updatedAt"] = now_iso()
        scene["subtitle"] = f"{scene['subtitle'].split(' V')[0]} V{scene['version']}"
        scene["narration"] = f"{scene['narration']} 這一幕已重新生成為第 {scene['version']} 版。"
        project["status"] = "Generating"
        project["updatedAt"] = now_iso()
        project.setdefault("renderHistory", []).append(
            {"type": "scene-regenerate", "sceneId": scene_id, "version": scene["version"], "at": now_iso()}
        )
        save_db(db)
    return render_project(project_id, preview=True, progress_callback=progress_callback)


def approve_project(project_id: str) -> dict:
    with DB_LOCK:
        db = load_db()
        project = find_item(db["projects"], project_id)
        project["status"] = "Approved"
        project["reviewStatus"] = "已批准"
        project["updatedAt"] = now_iso()
        save_db(db)
        return project


def delete_project(project_id: str) -> dict:
    with DB_LOCK:
        db = load_db()
        project = find_item(db["projects"], project_id)
        db["projects"] = [item for item in db["projects"] if item["id"] != project_id]
        save_db(db)
    return {"deleted": project_id, "keptProjectDir": project.get("projectDir"), "keptOutputDir": project.get("outputDir")}


def cancel_project(project_id: str) -> dict:
    with DB_LOCK:
        db = load_db()
        project = find_item(db["projects"], project_id)
        if project.get("status") in ["Completed", "Approved"]:
            raise ValueError("已完成或已批准的專案不可取消。")
        project["status"] = "Draft"
        project["updatedAt"] = now_iso()
        project.setdefault("renderHistory", []).append({"type": "cancel", "at": now_iso()})
        save_db(db)
        return project


def render_project(project_id: str, preview: bool, progress_callback=None) -> dict:
    with DB_LOCK:
        db = load_db()
        project = find_item(db["projects"], project_id)
        product = resolve_project_product(db, project)
        project["status"] = "Generating" if preview else "Exporting"
        project["updatedAt"] = now_iso()
        save_db(db)
    try:
        output = build_video_assets(
            project,
            product,
            preview=preview,
            progress_callback=progress_callback,
        )
        with DB_LOCK:
            db = load_db()
            project = find_item(db["projects"], project_id)
            project.update(output)
            project["status"] = "Ready for Preview" if preview else "Completed"
            project["reviewStatus"] = project.get("reviewStatus", "未審核")
            project["updatedAt"] = now_iso()
            project.setdefault("renderHistory", []).append(
                {"type": "preview" if preview else "export", "at": now_iso(), "path": output.get("previewVideo") or output.get("finalVideo")}
            )
            save_db(db)
            return project
    except Exception as error:
        if isinstance(error, JobCancelled):
            raise
        message = str(error)
        with DB_LOCK:
            db = load_db()
            project = find_item(db["projects"], project_id)
            project["status"] = "Partially Failed"
            project.setdefault("errors", []).append({"message": message, "at": now_iso()})
        db.setdefault("errors", []).append({"projectId": project_id, "message": message, "at": now_iso()})
        save_db(db)
        append_log("recovery.log", "project-render-failed", {"projectId": project_id, "message": message})
        return project


def export_project(project_id: str, progress_callback=None) -> dict:
    with DB_LOCK:
        project = find_item(load_db()["projects"], project_id)
        if project.get("status") not in ["Approved", "Ready for Preview", "Completed"]:
            raise ValueError("專案尚未準備好匯出")
    project = render_project(
        project_id,
        preview=False,
        progress_callback=progress_callback,
    )
    write_export_package(project)
    append_log("generation.log", "project-exported", {"projectId": project_id, "outputDir": project.get("outputDir")})
    return project


class JobCancelled(RuntimeError):
    pass


def get_job(job_id: str) -> dict:
    return find_item(load_db().get("jobs", []), job_id)


def job_provider_summary() -> tuple[str, str]:
    config = load_config()
    mode = config.get("providerMode", "local-first")
    if mode == "production":
        return "正式本機流程", "自動選擇"
    ffmpeg = Path(config.get("ffmpegPath") or detect_ffmpeg()).name
    return "本機優先", ffmpeg or "尚未選定"


def update_job(
    job_id: str,
    *,
    status: str | None = None,
    stage: str | None = None,
    progress: int | None = None,
    message: str | None = None,
    project_id: str | None = None,
    result: dict | None = None,
    error: dict | None = None,
) -> dict:
    with DB_LOCK:
        db = load_db()
        job = find_item(db["jobs"], job_id)
        if status:
            job["status"] = status
        if stage:
            previous_stage = job.get("currentStage", "")
            job["lastStage"] = previous_stage
            job["currentStage"] = stage
            if previous_stage != stage:
                job.setdefault("stageHistory", []).append(
                    {
                        "stage": stage,
                        "progress": int(progress if progress is not None else job.get("progress", 0)),
                        "message": message or "",
                        "at": now_iso(),
                    }
                )
        if progress is not None:
            job["progress"] = max(0, min(100, int(progress)))
        if message is not None:
            job["message"] = message
        if project_id is not None:
            job["projectId"] = project_id
        if result is not None:
            job["result"] = result
        if error is not None:
            job["error"] = error
        job["updatedAt"] = now_iso()
        started = datetime.fromisoformat(job.get("startedAt") or job["createdAt"])
        elapsed = max(0, int((datetime.now() - started).total_seconds()))
        job["elapsedSeconds"] = elapsed
        current_progress = int(job.get("progress", 0))
        if elapsed >= 2 and 5 <= current_progress < 96:
            job["etaSeconds"] = max(1, int(elapsed * (100 - current_progress) / current_progress))
        else:
            job["etaSeconds"] = None
        if status in {"completed", "failed", "cancelled"}:
            job["finishedAt"] = now_iso()
            job["etaSeconds"] = 0
        save_db(db)
        snapshot = dict(job)
    append_log(
        "jobs.log",
        "job-updated",
        {
            "jobId": job_id,
            "status": snapshot.get("status"),
            "stage": snapshot.get("currentStage"),
            "progress": snapshot.get("progress"),
            "projectId": snapshot.get("projectId"),
            "message": snapshot.get("message"),
        },
    )
    return snapshot


def ensure_job_not_cancelled(job_id: str) -> None:
    job = get_job(job_id)
    if job.get("cancelRequested") or job.get("status") in {"cancelling", "cancelled"}:
        raise JobCancelled("使用者已取消工作。")


def stage_reporter(job_id: str):
    def report(stage: str, progress: int, message: str) -> None:
        ensure_job_not_cancelled(job_id)
        update_job(
            job_id,
            status="running",
            stage=stage,
            progress=progress,
            message=message,
        )

    return report


def job_result(project: dict) -> dict:
    quality = (
        project.get("videoQuality", {}).get("overallScore")
        or project.get("visualQuality", {}).get("score")
        or project.get("visualQuality", {}).get("overallScore")
    )
    health = health_payload()
    return {
        "projectId": project["id"],
        "productId": project.get("productId", ""),
        "productName": project.get("productName", ""),
        "mode": project.get("mode", "product"),
        "status": project.get("status"),
        "outputDir": project.get("outputDir", ""),
        "previewVideo": project.get("previewVideo", ""),
        "finalVideo": project.get("finalVideo", ""),
        "qualityScore": quality,
        "emmaVersion": health.get("emmaCore", {}).get("activeIdentityVersion", "未啟用"),
        "voiceVersion": health.get("productionActivation", {}).get("voiceProfile", {}).get("version", "依正式設定"),
        "provider": get_job_provider(project.get("id", "")),
        "durationConflict": project.get("durationConflict"),
    }


def get_job_provider(_project_id: str) -> str:
    return job_provider_summary()[0]


def validate_job_payload(payload: dict) -> dict:
    action = str(payload.get("action", "create-project"))
    if action == "create-project":
        return {"action": action, "validation": validate_project_submission(payload)}
    if action not in {"render-project", "export-project", "regenerate-scene"}:
        raise ValueError("不支援此工作類型。")
    project_id = str(payload.get("projectId", "")).strip()
    project = find_item(load_db()["projects"], project_id)
    if action == "export-project" and project.get("status") not in {
        "Approved",
        "Ready for Preview",
        "Completed",
    }:
        raise ValueError("專案尚未準備好匯出。")
    if action == "regenerate-scene":
        scene = find_item(project.get("scenes", []), str(payload.get("sceneId", "")))
        if scene.get("approved"):
            raise ValueError("此場景已核准，請先編輯或取消核准後再重產。")
    return {"action": action, "project": project}


def create_job(payload: dict) -> tuple[dict, bool]:
    validation = validate_job_payload(payload)
    idempotency_key = str(payload.get("idempotencyKey", "")).strip() or uuid.uuid4().hex
    provider, model = job_provider_summary()
    with DB_LOCK:
        db = load_db()
        existing = next(
            (item for item in db.get("jobs", []) if item.get("idempotencyKey") == idempotency_key),
            None,
        )
        if existing:
            return dict(existing), True
        job = {
            "id": new_id("job"),
            "idempotencyKey": idempotency_key,
            "action": validation["action"],
            "status": "queued",
            "currentStage": "validation",
            "lastStage": "",
            "progress": 1,
            "message": "工作已建立，正在等待執行。",
            "provider": provider,
            "model": model,
            "projectId": str(payload.get("projectId", "")),
            "productId": str(payload.get("productId", "")),
            "productName": (
                validation.get("project", {}).get("productName", "")
                or (validation.get("validation", {}).get("product") or {}).get("name", "")
                or (
                    str(payload.get("textProjectName", "")).strip() or "純文字影片"
                    if payload.get("mode") == "text-only"
                    else ""
                )
            ),
            "payload": payload,
            "cancelRequested": False,
            "retryCount": 0,
            "maxRetries": 2,
            "elapsedSeconds": 0,
            "etaSeconds": None,
            "result": {},
            "error": {},
            "stageHistory": [
                {
                    "stage": "validation",
                    "progress": 1,
                    "message": "工作已建立，正在等待執行。",
                    "at": now_iso(),
                }
            ],
            "createdAt": now_iso(),
            "submittedAt": now_iso(),
            "updatedAt": now_iso(),
        }
        db.setdefault("jobs", []).append(job)
        save_db(db)
    append_log(
        "jobs.log",
        "job-created",
        {
            "jobId": job["id"],
            "action": job["action"],
            "productId": job["productId"],
            "idempotencyKey": idempotency_key,
        },
    )
    start_job(job["id"])
    return job, False


def start_job(job_id: str) -> None:
    with JOB_THREAD_LOCK:
        thread = ACTIVE_JOB_THREADS.get(job_id)
        if thread and thread.is_alive():
            return
        thread = threading.Thread(
            target=run_job,
            args=(job_id,),
            name=f"tpvg-{job_id}",
            daemon=True,
        )
        ACTIVE_JOB_THREADS[job_id] = thread
        thread.start()


def run_job(job_id: str) -> None:
    reporter = stage_reporter(job_id)
    try:
        job = get_job(job_id)
        payload = job.get("payload", {})
        action = job.get("action", "create-project")
        with DB_LOCK:
            db = load_db()
            live_job = find_item(db["jobs"], job_id)
            live_job["startedAt"] = live_job.get("startedAt") or now_iso()
            live_job["status"] = "running"
            live_job["updatedAt"] = now_iso()
            save_db(db)
        reporter("validation", 3, "需求驗證完成。")
        ensure_job_not_cancelled(job_id)

        if action == "create-project":
            validation = validate_project_submission(payload)
            product_name = (
                validation.get("product", {}).get("name")
                if validation.get("product")
                else str(payload.get("textProjectName", "")).strip() or "純文字影片"
            )
            update_job(job_id, stage="product", progress=8, message=f"已載入：{product_name}")
            reporter("research", 14, "已整理中文需求、商品知識與品牌規則。")
            reporter("script", 22, "正在建立腳本與內容結構。")
            project = create_project_record(payload, validation)
            update_job(job_id, project_id=project["id"])
            reporter("storyboard", 32, "腳本與分鏡規劃完成。")
            project = render_project(
                project["id"],
                preview=True,
                progress_callback=reporter,
            )
        elif action == "render-project":
            project = render_project(
                str(payload.get("projectId")),
                preview=True,
                progress_callback=reporter,
            )
        elif action == "export-project":
            reporter("editing", 89, "正在準備完整交付版本。")
            project = export_project(
                str(payload.get("projectId")),
                progress_callback=reporter,
            )
        else:
            reporter("storyboard", 32, "正在重建指定場景。")
            project = regenerate_scene(
                str(payload.get("projectId")),
                str(payload.get("sceneId")),
                progress_callback=reporter,
            )

        ensure_job_not_cancelled(job_id)
        if project.get("status") == "Partially Failed":
            message = project.get("errors", [{}])[-1].get("message", "影片生成失敗。")
            raise RuntimeError(message)
        update_job(
            job_id,
            status="completed",
            stage="export",
            progress=100,
            message="工作已完成，可預覽或開啟輸出資料夾。",
            project_id=project["id"],
            result=job_result(project),
        )
        append_log(
            "generation.log",
            "job-completed",
            {"jobId": job_id, "projectId": project["id"], "outputDir": project.get("outputDir")},
        )
    except JobCancelled:
        cleanup_job_temporary_files(job_id)
        update_job(
            job_id,
            status="cancelled",
            message="工作已安全取消，已清理暫存處理檔。",
        )
    except Exception as error:
        message = user_error(error)
        live_job = get_job(job_id)
        if is_retryable_failure(message) and int(live_job.get("retryCount", 0)) < int(live_job.get("maxRetries", 2)):
            with DB_LOCK:
                db = load_db()
                retrying = find_item(db["jobs"], job_id)
                retrying["retryCount"] = int(retrying.get("retryCount", 0)) + 1
                retrying["status"] = "queued"
                retrying["progress"] = max(1, int(retrying.get("progress", 1)) - 2)
                retrying["message"] = f"暫時性失敗，系統將自動重試（第 {retrying['retryCount']} 次）。"
                retrying["error"] = {
                    "stage": retrying.get("currentStage", "unknown"),
                    "reason": message,
                    "suggestedAction": "系統正在自動重試，無需重新送出。",
                    "at": now_iso(),
                    "log": "/api/logs/jobs.log",
                }
                retrying["updatedAt"] = now_iso()
                save_db(db)
            timer = threading.Timer(1.0, start_job, args=(job_id,))
            timer.daemon = True
            timer.start()
            append_log(
                "recovery.log",
                "job-auto-retry-scheduled",
                {"jobId": job_id, "error": message, "retryCount": live_job.get("retryCount", 0) + 1},
            )
            return
        update_job(
            job_id,
            status="failed",
            message="工作失敗，請依建議處理後重試。",
            error={
                "stage": get_job(job_id).get("currentStage", "unknown"),
                "reason": message,
                "suggestedAction": suggested_action(message),
                "at": now_iso(),
                "log": "/api/logs/jobs.log",
            },
        )
        append_log(
            "recovery.log",
            "job-failed",
            {"jobId": job_id, "error": message, "stage": get_job(job_id).get("currentStage")},
        )
    finally:
        with JOB_THREAD_LOCK:
            ACTIVE_JOB_THREADS.pop(job_id, None)


def suggested_action(message: str) -> str:
    lowered = message.lower()
    if "ffmpeg" in lowered:
        return "請到設定頁確認 FFmpeg 路徑後，再按「重試工作」。"
    if "comfy" in lowered:
        return "請啟動 ComfyUI 並確認連線狀態，或改用可用的本機模式。"
    if "emma" in lowered or "身分一致性" in message:
        return "系統會使用已核准的 Emma 參考重新處理；若仍失敗，請查看場景品質報告。"
    if "tts" in lowered or "聲音" in message:
        return "請檢查聲音工具狀態；內容與場景資料會保留，可直接重試。"
    if "照片" in message or "素材" in message:
        return "請回到商品資料庫補齊有效素材後重試。"
    return "請查看工作紀錄；修正顯示的問題後可直接重試，不需重新建立專案。"


def is_retryable_failure(message: str) -> bool:
    lowered = message.lower()
    return any(
        token in lowered
        for token in [
            "timeout",
            "timed out",
            "temporarily",
            "connection",
            "連線中斷",
            "暫時",
            "busy",
            "503",
            "429",
        ]
    )


def cancel_job(job_id: str) -> dict:
    with DB_LOCK:
        db = load_db()
        job = find_item(db["jobs"], job_id)
        if job.get("status") in {"completed", "failed", "cancelled"}:
            return dict(job)
        job["cancelRequested"] = True
        job["status"] = "cancelling"
        job["message"] = "正在安全取消，會在目前處理階段結束後停止。"
        job["updatedAt"] = now_iso()
        save_db(db)
        return dict(job)


def retry_job(job_id: str) -> dict:
    with DB_LOCK:
        db = load_db()
        job = find_item(db["jobs"], job_id)
        if job.get("status") not in {"failed", "cancelled"}:
            raise ValueError("只有失敗或已取消的工作可以重試。")
        if int(job.get("retryCount", 0)) >= int(job.get("maxRetries", 2)):
            raise ValueError("此工作已達自動重試上限，請先依錯誤建議修正。")
        job["retryCount"] = int(job.get("retryCount", 0)) + 1
        job["status"] = "queued"
        job["cancelRequested"] = False
        job["currentStage"] = "validation"
        job["progress"] = 1
        job["message"] = "工作已重新排入佇列。"
        job["error"] = {}
        job["result"] = {}
        job["startedAt"] = now_iso()
        job["finishedAt"] = ""
        job["updatedAt"] = now_iso()
        save_db(db)
        snapshot = dict(job)
    start_job(job_id)
    return snapshot


def cleanup_job_temporary_files(job_id: str) -> None:
    try:
        job = get_job(job_id)
        project_id = job.get("projectId")
        if not project_id:
            return
        temp_dir = (PROJECT_ROOT / project_id / "_job_tmp").resolve()
        if temp_dir.exists() and str(temp_dir).lower().startswith(str(PROJECT_ROOT).lower()):
            shutil.rmtree(temp_dir)
    except Exception as error:
        append_log("recovery.log", "job-temp-cleanup-failed", {"jobId": job_id, "error": str(error)})


def resume_pending_jobs() -> None:
    with DB_LOCK:
        db = load_db()
        pending_ids = []
        for job in db.get("jobs", []):
            if job.get("status") in {"queued", "running"}:
                job["status"] = "queued"
                job["message"] = "伺服器重新啟動，工作已自動恢復。"
                job["updatedAt"] = now_iso()
                pending_ids.append(job["id"])
            elif job.get("status") == "cancelling":
                job["status"] = "cancelled"
                job["message"] = "工作已在重新啟動時完成取消。"
                job["finishedAt"] = now_iso()
        save_db(db)
    for job_id in pending_ids:
        start_job(job_id)


def create_backup() -> dict:
    ensure_dirs()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = BACKUP_ROOT / f"temple-product-video-generator-backup-{stamp}.zip"
    with zipfile.ZipFile(backup_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in DATA_ROOT.rglob("*"):
            if not path.is_file():
                continue
            if BACKUP_ROOT in path.parents or EVIDENCE_ROOT in path.parents:
                continue
            archive.write(path, path.relative_to(DATA_ROOT))
    result = {"path": str(backup_path), "url": file_url(backup_path), "createdAt": now_iso()}
    append_log("recovery.log", "backup-created", {"path": str(backup_path)})
    return result


def restore_backup(file_payload: dict, confirm: str) -> dict:
    if confirm != "RESTORE":
        raise ValueError("還原前必須輸入 RESTORE 確認，避免誤覆蓋資料。")
    data_url = file_payload.get("data", "")
    if "," in data_url:
        data_url = data_url.split(",", 1)[1]
    backup = BACKUP_ROOT / f"restore-source-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
    backup.write_bytes(base64.b64decode(data_url))
    safety = create_backup()
    restore_root = DATA_ROOT / "_restore_tmp"
    if restore_root.exists():
        shutil.rmtree(restore_root)
    restore_root.mkdir(parents=True)
    with zipfile.ZipFile(backup, "r") as archive:
        archive.extractall(restore_root)
    required = restore_root / "database.json"
    if not required.exists():
        shutil.rmtree(restore_root)
        raise ValueError("備份檔缺少 database.json，已取消還原。")
    for child in restore_root.iterdir():
        target = DATA_ROOT / child.name
        if target.name in ["backups", "evidence", "_restore_tmp"]:
            continue
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        shutil.move(str(child), str(target))
    shutil.rmtree(restore_root, ignore_errors=True)
    append_log("recovery.log", "backup-restored", {"source": str(backup), "safetyBackup": safety.get("path")})
    return {"restored": True, "safetyBackup": safety}


def sanitize_config(config: dict) -> dict:
    blocked = ["api", "key", "token", "secret", "password"]
    result = {}
    for key, value in config.items():
        if any(word in key.lower() for word in blocked):
            result[key] = "[redacted]"
        else:
            result[key] = value
    return result


def create_support_package() -> dict:
    ensure_dirs()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    package_path = SUPPORT_ROOT / f"temple-product-video-generator-support-{stamp}.zip"
    summary = {
        "version": VERSION,
        "createdAt": now_iso(),
        "health": health_payload(),
        "config": sanitize_config(load_config()),
        "privacy": "Support package excludes product photos, generated videos, database contents, prompts, captions, narration, and customer-sensitive exports.",
    }
    summary_path = SUPPORT_ROOT / f"support-summary-{stamp}.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(summary_path, "support-summary.json")
        for path in LOG_ROOT.glob("*.log"):
            archive.write(path, f"logs/{path.name}")
    summary_path.unlink(missing_ok=True)
    append_log("app.log", "support-package-created", {"path": str(package_path)})
    return {"path": str(package_path), "url": file_url(package_path), "createdAt": now_iso()}


def create_evidence_screenshots() -> dict:
    db = seed_demo_data()
    if not db["projects"]:
        run_demo_project()
        db = load_db()
    project = db["projects"][-1]
    product = find_item(db["products"], project["productId"])
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target_dir = EVIDENCE_ROOT / stamp
    target_dir.mkdir(parents=True, exist_ok=True)
    screens = {
        "product-library": [
            "商品資料庫",
            f"商品：{product['name']}",
            f"照片數：{len(product.get('materials', []))}",
            "可操作：建立、更新、刪除、上傳、排序、替換、移除照片",
        ],
        "create-video": [
            "建立影片",
            "輸入：商品、平台、長度、目標受眾、繁體中文影片需求",
            "輸出：腳本、場景、旁白、字幕、Prompt、Metadata",
        ],
        "generation-progress": [
            "生成進度",
            f"目前狀態：{project['status']}",
            "支援：重試、取消未完成專案、錯誤紀錄、重新開啟恢復",
        ],
        "preview": [
            "影片預覽",
            f"預覽影片：{project.get('previewVideo', '未產生')}",
            f"場景數：{len(project.get('scenes', []))}",
        ],
        "scene-detail": [
            "場景細節",
            f"第一場：{project['scenes'][0]['purpose']}",
            "可操作：編輯、批准、單場景重生",
        ],
        "export": [
            "匯出",
            f"輸出資料夾：{project['outputDir']}",
            "檔案：MP4、SRT、旁白、Caption、Metadata、Prompts",
        ],
        "settings": [
            "設定",
            f"FFmpeg：{load_config().get('ffmpegPath', '')}",
            "可設定：ComfyUI、Whisper、TTS、輸出資料夾、字幕樣式",
        ],
    }
    created = []
    for name, lines in screens.items():
        path = target_dir / f"{name}.png"
        draw_evidence_image(path, lines)
        created.append({"screen": name, "path": str(path), "url": file_url(path)})
    return {"directory": str(target_dir), "screenshots": created}


def draw_evidence_image(path: Path, lines: list[str]) -> None:
    image = Image.new("RGB", (1440, 1000), "#f6f7f9")
    draw = ImageDraw.Draw(image)
    title_font = get_font(58)
    body_font = get_font(34)
    small_font = get_font(24)
    draw.rectangle((0, 0, 280, 1000), fill="#17231f")
    draw.text((34, 42), "Temple AI Studio", fill="#ffffff", font=body_font)
    nav = ["首頁", "商品資料庫", "建立影片", "生成進度", "影片預覽", "場景細節", "匯出", "設定"]
    y = 140
    for item in nav:
        draw.rounded_rectangle((28, y, 252, y + 48), radius=8, outline="#52645f", width=2)
        draw.text((48, y + 9), item, fill="#dce4e1", font=small_font)
        y += 64
    draw.rectangle((280, 0, 1440, 92), fill="#ffffff")
    draw.text((320, 22), lines[0], fill="#1c2430", font=title_font)
    draw.rounded_rectangle((320, 140, 1360, 850), radius=14, fill="#ffffff", outline="#d9dee8", width=2)
    y = 190
    for line in lines[1:]:
        wrapped = wrap_text(draw, line, body_font, 940)
        for part in wrapped:
            draw.text((370, y), part, fill="#1c2430", font=body_font)
            y += 54
        y += 18
    draw.text((370, 790), f"Application-side evidence generated at {now_iso()}", fill="#667085", font=small_font)
    image.save(path)


def create_release_package() -> dict:
    ensure_dirs()
    version_dir = RELEASE_ROOT / f"TempleProductVideoGenerator-{VERSION}"
    if version_dir.exists():
        shutil.rmtree(version_dir)
    version_dir.mkdir(parents=True)
    include_files = [
        "config.sample.json",
        "index.html",
        "package.json",
        "README.md",
        "server.py",
        "start.bat",
        "styles.css",
    ]
    for name in include_files:
        shutil.copy2(APP_ROOT / name, version_dir / name)
    shutil.copytree(APP_ROOT / "src", version_dir / "src")
    docs_dir = version_dir / "docs"
    docs_dir.mkdir()
    for name in [
        "V1_BACKUP_AND_RECOVERY.md",
        "V1_CEO_ACCEPTANCE_REPORT.md",
        "V1_FINAL_QA_REPORT.md",
        "V1_IMPLEMENTATION_REPORT.md",
        "V1_USER_QUICKSTART_ZH_TW.md",
        "V1_KNOWN_LIMITATIONS.md",
        "V1_OPERATOR_HANDOFF.md",
        "V1_PRODUCTION_DEPLOYMENT_REPORT.md",
        "V1_PRODUCTION_PATHS.md",
        "V1_RELEASE_MANIFEST.md",
        "V1_RELEASE_NOTES.md",
        "V1_SUPPORT_AND_DIAGNOSTICS.md",
        "V1_UPGRADE_AND_ROLLBACK.md",
        "V1_VALIDATION_REPORT.md",
    ]:
        source = APP_ROOT.parent.parent / "docs" / name
        if source.exists():
            shutil.copy2(source, docs_dir / name)
    sample_dir = version_dir / "sample-data"
    sample_dir.mkdir()
    make_demo_image(sample_dir / "sample-product-photo.png")
    (sample_dir / "sample-product-project.json").write_text(
        json.dumps(
            {
                "product": {
                    "name": "Temple Energy Candle",
                    "category": "能量蠟燭",
                    "description": "以日常靜心與空間儀式為核心的手作蠟燭。",
                    "sellingPoint": "讓使用者在忙碌生活裡建立一個穩定、安靜、可重複的儀式時刻。",
                    "spiritualInfo": "適合冥想、睡前整理心緒、日常祝福與空間淨化感的情境。",
                    "targetAudience": "喜歡質感生活、身心靈日常與送禮儀式感的使用者。",
                },
                "videoRequest": "請製作一支溫柔、清楚、有儀式感的商品短影片。",
                "platform": "Instagram Reels",
                "duration": 24,
                "samplePhoto": "sample-product-photo.png",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (version_dir / "VERSION.txt").write_text(VERSION, encoding="utf-8")
    (version_dir / "README_ZH_TW.txt").write_text(
        "Temple Product Video Generator V1\n\n請執行 start.bat 啟動。\n資料會建立在本資料夾的 data 目錄。\n不要直接刪除 data，除非已備份。\n",
        encoding="utf-8",
    )
    zip_base = RELEASE_ROOT / f"TempleProductVideoGenerator-{VERSION}"
    archive_path = shutil.make_archive(str(zip_base), "zip", version_dir)
    return {"folder": str(version_dir), "archive": archive_path}


def build_video_assets(
    project: dict,
    product: dict,
    preview: bool,
    progress_callback=None,
) -> dict:
    report = progress_callback or (lambda *_args, **_kwargs: None)
    config = load_config()
    if config.get("providerMode") == "production":
        report("images", 44, "正在執行正式影像與素材流程。")
        output = build_real_production_assets(project, product, preview)
        report("emma", 54, "Emma 一致性與素材品質檢查完成。")
        report("video", 66, "正式影片生成完成。")
        report("audio", 74, "聲音同步檢查完成。")
        report("subtitles", 82, "字幕檢查完成。")
        report("editing", 89, "剪輯組合完成。")
        report("render", 96, "MP4 渲染完成。")
        return output
    ffmpeg = config.get("ffmpegPath") or detect_ffmpeg()
    if not ffmpeg or not Path(ffmpeg).exists():
        raise RuntimeError("找不到 FFmpeg，暫時無法輸出 MP4。")
    output_dir = Path(project["outputDir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    material_paths = [
        Path(m["path"])
        for m in product.get("materials", [])
        if m.get("kind", "image") in {"image", "logo"} and Path(m["path"]).exists()
    ]
    if not material_paths and project.get("mode") != "text-only":
        raise RuntimeError("請先上傳至少一張商品照片。")

    report("images", 44, "正在建立並評估場景影像。")
    visual_report = run_image_pipeline(
        project,
        product,
        Path(project["projectDir"]),
        emma_root=production_data_root(),
    )
    if visual_report.get("quality", {}).get("overall") != "PASS":
        append_log("generation.log", "visual-pipeline-quality-failed", {"projectId": project["id"], "quality": visual_report.get("quality")})
        quality = visual_report.get("quality", {})
        failed_scenes = quality.get("failedScenes", [])
        failed_checks = sorted(
            {
                check
                for item in quality.get("reports", [])
                if item.get("overall") != "PASS"
                for check in item.get("failedChecks", [])
            }
        )
        check_labels = {
            "emmaIdentityConsistency": "Emma 身分一致性",
            "productVisibility": "商品可見度",
            "promptQuality": "提示詞品質",
            "resolution": "解析度",
            "aspectRatio": "畫面比例",
            "composition": "構圖",
            "textReadability": "文字可讀性",
            "subtitleContrast": "字幕對比",
            "sharpness": "清晰度",
            "commercialUsability": "商業可用性",
        }
        scene_text = "、".join(failed_scenes) or "未知場景"
        check_text = "、".join(check_labels.get(item, item) for item in failed_checks) or "整體品質"
        raise RuntimeError(f"圖片品質檢查未通過：{scene_text}（{check_text}）。系統已完成自動修復嘗試。")

    report("emma", 54, "Emma 與商品視覺一致性檢查完成。")
    report("video", 66, "正在生成並組合影片畫面。")
    video_report = run_video_generation_pipeline(project, product, output_dir, Path(project["projectDir"]), Path(ffmpeg), preview=preview)
    report("audio", 74, "聲音軌與影片時間軸已同步。")
    report("subtitles", 82, "字幕檔與燒錄版本已建立。")
    report("editing", 89, "場景剪輯與轉場已完成。")
    report("render", 96, "影片渲染與播放檢查完成。")
    target = Path(video_report["outputVideo"])
    srt_path = Path(video_report["subtitles"])
    return {
        "previewVideo": file_url(target) if preview else project.get("previewVideo"),
        "finalVideo": file_url(target) if not preview else project.get("finalVideo"),
        "subtitles": file_url(srt_path),
        "ffmpegPath": ffmpeg,
        "scenes": project["scenes"],
        "storyboard": visual_report.get("storyboard"),
        "providerPrompts": visual_report.get("providerPrompts"),
        "visualQuality": visual_report.get("quality"),
        "visualPipelineReport": str(Path(project["projectDir"]) / "visual-pipeline-report.json"),
        "assetIndex": visual_report.get("assetIndex"),
        "videoIntelligence": video_report,
        "videoIntelligenceReport": str(Path(project["projectDir"]) / ("video-intelligence-preview-report.json" if preview else "video-intelligence-final-report.json")),
        "videoQuality": video_report.get("quality"),
        "videoSpec": "1080x1920, MP4, local FFmpeg motion pipeline, silent sync audio track, subtitles burned into frames",
    }


def build_real_production_assets(project: dict, product: dict, preview: bool) -> dict:
    production_root = Path(
        os.environ.get(
            "TEMPLE_PRODUCTION_DATA_ROOT",
            REPO_ROOT.parent / "Temple AI Studio Production Data",
        )
    ).resolve()
    run_id = (
        f"{project['id']}-{'preview' if preview else 'export'}-"
        f"{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    )
    request = {
        "runId": run_id,
        "request": project.get("requirement")
        or f"請為{product.get('name', '此商品')}製作神殿商品影片。",
        "product": product,
        "scriptPackage": {
            key: project[key]
            for key in [
                "requirement",
                "platform",
                "targetAudience",
                "duration",
                "script",
                "scenes",
                "prompts",
                "caption",
                "tags",
                "seoKeywords",
                "thumbnailSuggestion",
                "metadata",
                "quality",
            ]
            if key in project
        },
        "scenarioType": "product-introduction",
        "duration": project.get("duration", 30),
        "platform": project.get("platform", "Instagram Reels"),
        "aspectRatio": "9:16",
        "researchRequired": False,
    }
    workflow = RealProductionWorkflow(REPO_ROOT, production_root)
    try:
        result = workflow.run(request)
    except ProductionWorkflowBlocked as error:
        messages = [
            item.get("message", item.get("code", "未知阻擋"))
            for item in error.report.get("blockers", [])
        ]
        raise RuntimeError("生產模式尚未就緒：" + "；".join(messages)) from error
    output_dir = Path(project["outputDir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / ("preview_video.mp4" if preview else "final_video.mp4")
    subtitles = output_dir / "subtitles.zh-TW.srt"
    shutil.copy2(Path(result["exportPath"]), target)
    source_subtitles = (
        production_root
        / "projects"
        / run_id
        / "export"
        / "subtitles.zh-TW.srt"
    )
    shutil.copy2(source_subtitles, subtitles)
    quality_path = production_root / "projects" / run_id / "quality-evidence.json"
    quality = json.loads(quality_path.read_text(encoding="utf-8-sig"))
    return {
        "previewVideo": file_url(target) if preview else project.get("previewVideo"),
        "finalVideo": file_url(target) if not preview else project.get("finalVideo"),
        "subtitles": file_url(subtitles),
        "ffmpegPath": result.get("ffmpeg"),
        "scenes": project["scenes"],
        "storyboard": json.loads(
            (production_root / "projects" / run_id / "storyboard.json").read_text(
                encoding="utf-8-sig"
            )
        ),
        "providerPrompts": json.loads(
            (
                production_root / "projects" / run_id / "provider-prompts.json"
            ).read_text(encoding="utf-8-sig")
        ),
        "visualQuality": quality,
        "videoQuality": quality,
        "commercialRun": str(
            production_root / "projects" / run_id / "commercial-run.json"
        ),
        "videoSpec": "真實本機 AI Provider、Emma 身分與聲音、唇同步、繁中字幕、FFmpeg 商業輸出",
    }

def write_export_package(project: dict) -> None:
    output_dir = Path(project["outputDir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "narration.txt").write_text(project["script"], encoding="utf-8")
    (output_dir / "caption.txt").write_text(project["caption"], encoding="utf-8")
    (output_dir / "metadata.json").write_text(json.dumps(project["metadata"], ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "scenes.json").write_text(json.dumps(project["scenes"], ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "prompts.json").write_text(json.dumps(project["prompts"], ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "storyboard.json").write_text(json.dumps(project.get("storyboard", {}), ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "provider_prompts.json").write_text(json.dumps(project.get("providerPrompts", {}), ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "visual_quality.json").write_text(json.dumps(project.get("visualQuality", {}), ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "video_intelligence.json").write_text(json.dumps(project.get("videoIntelligence", {}), ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "video_quality.json").write_text(json.dumps(project.get("videoQuality", {}), ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "temple_os.json").write_text(json.dumps(temple_os_status(), ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "emma_core.json").write_text(
        json.dumps(
            {
                "status": health_payload().get("emmaCore"),
                "sceneUsage": [
                    {
                        "sceneId": scene.get("id"),
                        "required": scene.get("emmaCore", {}).get("required"),
                        "referenceSelection": scene.get("emmaCore", {}).get("referenceSelection", {}).get("overall"),
                        "consistency": scene.get("emmaCore", {}).get("consistency", {}).get("overall"),
                    }
                    for scene in project.get("scenes", [])
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    if project.get("assetIndex") and Path(project["assetIndex"]).exists():
        shutil.copyfile(project["assetIndex"], output_dir / "asset_index.json")
    (output_dir / "thumbnail_suggestion.txt").write_text(project["thumbnailSuggestion"], encoding="utf-8")
    db = load_db()
    product = resolve_project_product(db, project)
    material_lines = [f"{m['fileName']} | {m['path']}" for m in product.get("materials", [])]
    (output_dir / "materials_used.txt").write_text("\n".join(material_lines), encoding="utf-8")
    final = output_dir / "final_video.mp4"
    subtitled = output_dir / "final_video_subtitled.mp4"
    if final.exists() and not subtitled.exists():
        shutil.copyfile(final, subtitled)


def file_url(path: Path) -> str:
    resolved = path.resolve()
    try:
        return "/api/files/" + resolved.relative_to(DATA_ROOT).as_posix()
    except ValueError:
        output_root = Path(load_config().get("outputDir") or EXPORT_ROOT).resolve()
        try:
            return "/api/output-files/" + resolved.relative_to(output_root).as_posix()
        except ValueError:
            return ""


def open_local_path(value: str) -> dict:
    target = Path(str(value or "")).resolve()
    allowed_roots = {
        DATA_ROOT,
        Path(load_config().get("outputDir") or EXPORT_ROOT).resolve(),
        production_data_root(),
    }
    if not any(
        target == root or str(target).lower().startswith(str(root).lower() + os.sep)
        for root in allowed_roots
    ):
        raise ValueError("只能開啟 Temple AI Studio 的資料或輸出位置。")
    if not target.exists():
        raise ValueError("指定位置尚不存在。")
    if hasattr(os, "startfile"):
        os.startfile(str(target))  # type: ignore[attr-defined]
    else:
        raise RuntimeError("目前系統不支援自動開啟資料夾。")
    return {"path": str(target), "opened": True}


def json_response(handler: SimpleHTTPRequestHandler, payload, status: int = 200) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
    handler.send_header("Pragma", "no-cache")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def read_json(handler: SimpleHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0") or "0")
    if length == 0:
        return {}
    raw = handler.rfile.read(length)
    return json.loads(raw.decode("utf-8"))


def error_response_payload(error: Exception) -> dict:
    payload = {"ok": False, "message": user_error(error)}
    field_errors = getattr(error, "field_errors", None)
    if field_errors:
        payload["fieldErrors"] = field_errors
    return payload


class AppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(APP_ROOT), **kwargs)

    def log_message(self, fmt, *args):
        message = fmt % args
        sys.stdout.write("[%s] %s\n" % (now_iso(), message))
        append_log("app.log", "http-request", {"message": message})

    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            path = parsed.path
            if path == "/api/health":
                return json_response(self, health_payload())
            if path == "/api/state":
                return json_response(self, {"db": load_db(), "config": load_config(), "health": health_payload()})
            if path.startswith("/api/jobs/"):
                return json_response(self, {"ok": True, "job": get_job(path.rsplit("/", 1)[-1])})
            if path.startswith("/api/logs/"):
                return self.serve_log(path.rsplit("/", 1)[-1])
            if path.startswith("/api/files/"):
                return self.serve_data_file(path.removeprefix("/api/files/"))
            if path.startswith("/api/output-files/"):
                return self.serve_output_file(path.removeprefix("/api/output-files/"))
            if path == "/api/evidence/screenshots":
                return json_response(self, {"ok": True, **create_evidence_screenshots()})
            if path == "/api/release/package":
                return json_response(self, {"ok": True, **create_release_package()})
            if path == "/api/support/package":
                return json_response(self, {"ok": True, "supportPackage": create_support_package()})
            if path.startswith("/api/export-package/"):
                project_id = path.rsplit("/", 1)[-1]
                project = find_item(load_db()["projects"], project_id)
                write_export_package(project)
                return json_response(self, {"ok": True, "outputDir": project["outputDir"]})
            return super().do_GET()
        except Exception as error:
            return json_response(self, error_response_payload(error), 400)

    def do_POST(self):
        try:
            path = urlparse(self.path).path
            payload = read_json(self)
            if path == "/api/settings":
                return json_response(self, {"ok": True, "config": save_config(payload)})
            if path == "/api/products":
                return json_response(self, {"ok": True, "product": create_product(payload)})
            if path.endswith("/materials") and path.startswith("/api/products/"):
                product_id = path.split("/")[3]
                return json_response(
                    self,
                    {
                        "ok": True,
                        **add_materials(
                            product_id,
                            payload.get("files", []),
                            payload.get("kind", ""),
                        ),
                    },
                )
            if path == "/api/jobs":
                job, duplicate = create_job(payload)
                return json_response(
                    self,
                    {"ok": True, "job": job, "duplicate": duplicate},
                    200 if duplicate else 202,
                )
            if path == "/api/projects":
                return json_response(self, {"ok": True, "project": create_project(payload)})
            if path == "/api/demo/run":
                return json_response(self, {"ok": True, "project": run_demo_project()})
            if path == "/api/backup":
                return json_response(self, {"ok": True, "backup": create_backup()})
            if path == "/api/restore":
                return json_response(self, {"ok": True, **restore_backup(payload.get("file", {}), payload.get("confirm", ""))})
            if path == "/api/open-path":
                return json_response(self, {"ok": True, **open_local_path(payload.get("path", ""))})
            match = re.match(r"^/api/jobs/([^/]+)/(cancel|retry)$", path)
            if match:
                job_id, action = match.groups()
                job = cancel_job(job_id) if action == "cancel" else retry_job(job_id)
                return json_response(self, {"ok": True, "job": job})
            match = re.match(r"^/api/projects/([^/]+)/(approve|export|render)$", path)
            if match:
                project_id, action = match.groups()
                if action == "approve":
                    return json_response(self, {"ok": True, "project": approve_project(project_id)})
                if action == "render":
                    return json_response(self, {"ok": True, "project": render_project(project_id, preview=True)})
                if action == "export":
                    return json_response(self, {"ok": True, "project": export_project(project_id)})
            match = re.match(r"^/api/projects/([^/]+)/(approve|export|render|cancel)$", path)
            if match:
                project_id, action = match.groups()
                if action == "cancel":
                    return json_response(self, {"ok": True, "project": cancel_project(project_id)})
            match = re.match(r"^/api/projects/([^/]+)/scenes/([^/]+)/(update|approve|regenerate)$", path)
            if match:
                project_id, scene_id, action = match.groups()
                if action == "update":
                    return json_response(self, {"ok": True, "project": update_scene(project_id, scene_id, payload)})
                if action == "approve":
                    return json_response(self, {"ok": True, "project": approve_scene(project_id, scene_id)})
                if action == "regenerate":
                    return json_response(self, {"ok": True, "project": regenerate_scene(project_id, scene_id)})
            return json_response(self, {"ok": False, "message": "找不到 API 路徑"}, 404)
        except Exception as error:
            return json_response(self, error_response_payload(error), 400)

    def do_PUT(self):
        try:
            path = urlparse(self.path).path
            payload = read_json(self)
            match = re.match(r"^/api/products/([^/]+)$", path)
            if match:
                return json_response(self, {"ok": True, "product": update_product(match.group(1), payload)})
            match = re.match(r"^/api/products/([^/]+)/materials/([^/]+)/(replace|move)$", path)
            if match:
                product_id, material_id, action = match.groups()
                if action == "replace":
                    return json_response(self, {"ok": True, "material": replace_material(product_id, material_id, payload.get("file", {}))})
                if action == "move":
                    return json_response(self, {"ok": True, **move_material(product_id, material_id, payload.get("direction", "down"))})
            return json_response(self, {"ok": False, "message": "找不到 API 路徑"}, 404)
        except Exception as error:
            return json_response(self, error_response_payload(error), 400)

    def do_DELETE(self):
        try:
            path = urlparse(self.path).path
            match = re.match(r"^/api/products/([^/]+)/materials/([^/]+)$", path)
            if match:
                return json_response(self, {"ok": True, **delete_material(match.group(1), match.group(2))})
            match = re.match(r"^/api/products/([^/]+)$", path)
            if match:
                return json_response(self, {"ok": True, **delete_product(match.group(1))})
            match = re.match(r"^/api/projects/([^/]+)$", path)
            if match:
                return json_response(self, {"ok": True, **delete_project(match.group(1))})
            return json_response(self, {"ok": False, "message": "找不到 API 路徑"}, 404)
        except Exception as error:
            return json_response(self, error_response_payload(error), 400)

    def serve_log(self, name: str):
        allowed = {"app.log", "jobs.log", "generation.log", "recovery.log", "ffmpeg-error.log"}
        if name not in allowed:
            self.send_error(HTTPStatus.NOT_FOUND, "Log not found")
            return
        target = LOG_ROOT / name
        body = target.read_bytes() if target.exists() else b""
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def serve_data_file(self, rel: str):
        target = (DATA_ROOT / unquote(rel)).resolve()
        if not str(target).lower().startswith(str(DATA_ROOT).lower()) or not target.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return
        return self.serve_static_path(target)

    def serve_output_file(self, rel: str):
        output_root = Path(load_config().get("outputDir") or EXPORT_ROOT).resolve()
        target = (output_root / unquote(rel)).resolve()
        if not str(target).lower().startswith(str(output_root).lower()) or not target.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return
        return self.serve_static_path(target)

    def serve_static_path(self, target: Path):
        ctype = "application/octet-stream"
        if target.suffix.lower() == ".mp4":
            ctype = "video/mp4"
        elif target.suffix.lower() == ".png":
            ctype = "image/png"
        elif target.suffix.lower() in [".jpg", ".jpeg"]:
            ctype = "image/jpeg"
        elif target.suffix.lower() == ".srt":
            ctype = "text/plain; charset=utf-8"
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def user_error(error: Exception) -> str:
    if isinstance(error, KeyError):
        return str(error).strip("'") or "找不到指定資料"
    if isinstance(error, ValueError):
        return str(error)
    return f"操作失敗：{error}"


def run_demo_project() -> dict:
    db = seed_demo_data()
    product = db["products"][0]
    project = create_project(
        {
            "productId": product["id"],
            "platform": "Instagram Reels",
            "duration": 24,
            "targetAudience": product.get("targetAudience", ""),
            "spiritualInfo": product.get("spiritualInfo", ""),
            "requirement": "請製作一支溫柔、清楚、有儀式感的商品短影片。",
        }
    )
    scene = next((item for item in project["scenes"] if item["purpose"] == "Product Features"), project["scenes"][2])
    project = regenerate_scene(project["id"], scene["id"])
    project = approve_project(project["id"])
    project = export_project(project["id"])
    return project


def smoke_test() -> int:
    project = run_demo_project()
    output_dir = Path(project["outputDir"])
    required = [
        output_dir / "final_video.mp4",
        output_dir / "final_video_subtitled.mp4",
        output_dir / "subtitles.srt",
        output_dir / "narration.txt",
        output_dir / "caption.txt",
        output_dir / "metadata.json",
        output_dir / "scenes.json",
        output_dir / "prompts.json",
        output_dir / "storyboard.json",
        output_dir / "provider_prompts.json",
        output_dir / "visual_quality.json",
        output_dir / "video_intelligence.json",
        output_dir / "video_quality.json",
        output_dir / "emma_core.json",
        output_dir / "asset_index.json",
        output_dir / "thumbnail_suggestion.txt",
        output_dir / "materials_used.txt",
    ]
    missing = [str(path) for path in required if not path.exists() or path.stat().st_size == 0]
    result = {
        "ok": not missing and project["status"] == "Completed",
        "projectId": project["id"],
        "status": project["status"],
        "finalVideo": str(output_dir / "final_video.mp4"),
        "missing": missing,
        "ffmpeg": project.get("ffmpegPath", ""),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


def main() -> int:
    ensure_dirs()
    if "--smoke-test" in sys.argv:
        return smoke_test()
    resume_pending_jobs()
    host = "127.0.0.1"
    port = int(os.environ.get("TPVG_PORT", "4173"))
    server = ThreadingHTTPServer((host, port), AppHandler)
    print(f"Temple Product Video Generator V1 running at http://{host}:{port}")
    print(f"Data: {DATA_ROOT}")
    db_health = database_health()
    print(f"Database: {db_health['path']}")
    print(
        "Database status: "
        f"readable={db_health['readable']} writable={db_health['writable']} "
        f"migration={db_health['migrationStatus']} products={db_health['productCount']}"
    )
    append_log(
        "app.log",
        "server-started",
        {
            "host": host,
            "port": port,
            "dataRoot": str(DATA_ROOT),
            "version": VERSION,
            "database": db_health,
            "apiHealth": "正常",
        },
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Server stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
