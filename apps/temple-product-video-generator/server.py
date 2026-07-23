from __future__ import annotations

import base64
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

from PIL import Image, ImageDraw, ImageFilter, ImageFont


APP_ROOT = Path(__file__).resolve().parent
DATA_ROOT = Path(os.environ.get("TPVG_DATA_DIR", APP_ROOT / "data")).resolve()
DB_PATH = DATA_ROOT / "database.json"
CONFIG_PATH = DATA_ROOT / "config.json"
UPLOAD_ROOT = DATA_ROOT / "uploads"
PROJECT_ROOT = DATA_ROOT / "projects"
EXPORT_ROOT = DATA_ROOT / "exports"
RUNTIME_ROOT = APP_ROOT / "runtime"
BACKUP_ROOT = DATA_ROOT / "backups"
EVIDENCE_ROOT = DATA_ROOT / "evidence"
RELEASE_ROOT = APP_ROOT / "release"
VERSION = "1.0.0"

FRAME_SIZE = (1080, 1920)
FPS = 25
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


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"


def safe_name(value: str, fallback: str = "item") -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", value or "").strip(" .")
    value = re.sub(r"\s+", "-", value)
    return value[:90] or fallback


def ensure_dirs() -> None:
    for path in [DATA_ROOT, UPLOAD_ROOT, PROJECT_ROOT, EXPORT_ROOT, RUNTIME_ROOT, BACKUP_ROOT, EVIDENCE_ROOT, RELEASE_ROOT]:
        path.mkdir(parents=True, exist_ok=True)


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
        "schemaVersion": 1,
        "products": [],
        "projects": [],
        "errors": [],
        "createdAt": now_iso(),
        "updatedAt": now_iso(),
    }


def load_config() -> dict:
    ensure_dirs()
    if not CONFIG_PATH.exists():
        atomic_write_json(CONFIG_PATH, default_config())
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


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
    current["updatedAt"] = now_iso()
    atomic_write_json(CONFIG_PATH, current)
    return current


def load_db() -> dict:
    ensure_dirs()
    if not DB_PATH.exists():
        atomic_write_json(DB_PATH, empty_db())
    db = json.loads(DB_PATH.read_text(encoding="utf-8"))
    db.setdefault("products", [])
    db.setdefault("projects", [])
    db.setdefault("errors", [])
    return db


def save_db(db: dict) -> None:
    db["updatedAt"] = now_iso()
    atomic_write_json(DB_PATH, db)


def detect_ffmpeg() -> str:
    candidates = [
        shutil.which("ffmpeg"),
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


def health_payload() -> dict:
    config = load_config()
    ffmpeg = config.get("ffmpegPath") or detect_ffmpeg()
    return {
        "status": "ok",
        "time": now_iso(),
        "dataRoot": str(DATA_ROOT),
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
        "spiritualInfo": str(payload.get("spiritualInfo", "")).strip(),
        "targetAudience": str(payload.get("targetAudience", "")).strip(),
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
        for key in ["name", "category", "description", "sellingPoint", "spiritualInfo", "targetAudience"]:
            if key in payload:
                product[key] = str(payload.get(key, "")).strip()
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


def add_materials(product_id: str, files: list[dict]) -> dict:
    if not files:
        raise ValueError("請至少選擇一張商品照片")
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
                raise ValueError("單張圖片不可超過 25MB")
            suffix = Path(raw_name).suffix.lower()
            if suffix not in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]:
                raise ValueError("僅支援 PNG、JPG、WEBP、BMP 圖片")
            material_id = new_id("material")
            path = target_dir / f"{material_id}{suffix}"
            path.write_bytes(blob)
            with Image.open(path) as img:
                width, height = img.size
                img.verify()
            material = {
                "id": material_id,
                "fileName": raw_name,
                "mime": item.get("type", "image/*"),
                "path": str(path),
                "url": image_url(str(path)),
                "role": "商品照片" if next_order > 1 else "主商品照片",
                "order": next_order,
                "width": width,
                "height": height,
                "createdAt": now_iso(),
            }
            product.setdefault("materials", []).append(material)
            saved.append(material)
            next_order += 1
        product["updatedAt"] = now_iso()
        save_db(db)
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
    total_duration = int(payload.get("duration") or load_config().get("defaultDuration", 30))
    total_duration = max(18, min(60, total_duration))
    durations = split_durations(total_duration)
    audience = payload.get("targetAudience") or product.get("targetAudience") or "重視質感生活與日常儀式感的使用者"
    requirement = payload.get("requirement") or "做一支溫柔、有儀式感、適合社群發布的商品短影片。"
    cultural = payload.get("spiritualInfo") or product.get("spiritualInfo") or "以安定、祝福、專注與日常陪伴作為核心價值。"
    platform = payload.get("platform") or "Instagram Reels"
    scene_specs = [
        ("Hook", "用安靜但有吸引力的第一眼抓住注意力", f"你是否也想在忙碌裡，留一個安定自己的片刻？", f"為自己留一個安定片刻"),
        ("Introduction", "清楚介紹商品與用途", f"這是{product['name']}，為日常儀式與平靜空間而準備。", f"{product['name']}"),
        ("Product Features", "呈現商品特色與細節", f"{product['sellingPoint']}，讓每一次使用都更容易被感受。", "看得見的細節與質感"),
        ("Spiritual Value", "連結靈性與文化價值", f"{cultural}，不誇大承諾，只陪你回到當下。", "把注意力帶回當下"),
        ("CTA", "給出溫和行動呼籲", f"如果你也想建立自己的儀式感，可以從{product['name']}開始。", "從一份日常儀式開始"),
        ("Ending", "完成品牌收尾", "願每一天，都有一個能讓心安定下來的小小開始。", "Temple AI Studio"),
    ]
    scenes = []
    prompts = []
    cursor = 0.0
    for index, (purpose, visual_goal, narration, subtitle) in enumerate(scene_specs):
        duration = durations[index]
        scene_id = f"scene-{index + 1:02d}-{purpose.lower().replace(' ', '-')}"
        start = cursor
        end = cursor + duration
        cursor = end
        prompt = (
            f"以真實商品照片為核心，保持商品外觀、Logo、文字與主要細節不變。"
            f"場景目的：{purpose}。畫面方向：{visual_goal}。平台：{platform}。"
        )
        scenes.append(
            {
                "id": scene_id,
                "order": index + 1,
                "purpose": purpose,
                "duration": duration,
                "start": round(start, 2),
                "end": round(end, 2),
                "visualDescription": visual_goal,
                "narration": narration,
                "subtitle": subtitle,
                "prompt": prompt,
                "music": "V1 預設無版權風險，若未設定音樂則輸出無背景音樂版本。",
                "transition": "柔和淡入淡出",
                "status": "Ready for Preview",
                "approved": False,
                "version": 1,
                "updatedAt": now_iso(),
            }
        )
        prompts.append(
            {
                "id": new_id("prompt"),
                "sceneId": scene_id,
                "category": "video",
                "text": prompt,
                "createdAt": now_iso(),
            }
        )
    caption = f"{product['name']}｜把日常變成一個可以安定下來的儀式。"
    tags = unique_list(["Temple", product["category"], "儀式感", "質感生活", "身心靈", platform])
    metadata = {
        "projectId": project_id,
        "productName": product["name"],
        "productCategory": product["category"],
        "targetAudience": audience,
        "platform": platform,
        "language": "繁體中文",
        "duration": total_duration,
        "sceneCount": len(scenes),
        "providerMode": "local-template + ffmpeg",
        "createdAt": now_iso(),
        "sourceMaterials": [m["fileName"] for m in product.get("materials", [])],
    }
    return {
        "requirement": requirement,
        "platform": platform,
        "targetAudience": audience,
        "duration": total_duration,
        "script": "\n".join([scene["narration"] for scene in scenes]),
        "scenes": scenes,
        "prompts": prompts,
        "caption": caption,
        "tags": tags,
        "seoKeywords": unique_list([product["name"], product["category"], "Temple", "儀式感", "平靜", "祝福"]),
        "thumbnailSuggestion": f"使用{product['name']}最清楚的直式主視覺，封面字控制在 8 個中文字內。",
        "metadata": metadata,
    }


def split_durations(total: int) -> list[int]:
    weights = [0.12, 0.17, 0.24, 0.2, 0.15, 0.12]
    values = [max(2, round(total * weight)) for weight in weights]
    diff = total - sum(values)
    values[-1] += diff
    return values


def unique_list(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        item = str(item).strip()
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def create_project(payload: dict) -> dict:
    with DB_LOCK:
        db = load_db()
        product = find_item(db["products"], payload.get("productId", ""))
        if not product.get("materials"):
            raise ValueError("請先上傳至少一張商品照片")
        project_id = new_id("project")
        content = generate_content(product, payload, project_id)
        configured_output = Path(load_config().get("outputDir") or EXPORT_ROOT).resolve()
        project_dir = PROJECT_ROOT / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        project = {
            "id": project_id,
            "productId": product["id"],
            "productName": product["name"],
            "status": "Planning",
            "reviewStatus": "未審核",
            "createdAt": now_iso(),
            "updatedAt": now_iso(),
            "outputDir": str(configured_output / project_id),
            "projectDir": str(project_dir),
            "renderHistory": [],
            "errors": [],
            **content,
        }
        db["projects"].append(project)
        save_db(db)
    return render_project(project_id, preview=True)


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


def regenerate_scene(project_id: str, scene_id: str) -> dict:
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
    return render_project(project_id, preview=True)


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


def render_project(project_id: str, preview: bool) -> dict:
    with DB_LOCK:
        db = load_db()
        project = find_item(db["projects"], project_id)
        product = find_item(db["products"], project["productId"])
        project["status"] = "Generating" if preview else "Exporting"
        project["updatedAt"] = now_iso()
        save_db(db)
    try:
        output = build_video_assets(project, product, preview=preview)
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
        message = str(error)
        with DB_LOCK:
            db = load_db()
            project = find_item(db["projects"], project_id)
            project["status"] = "Partially Failed"
            project.setdefault("errors", []).append({"message": message, "at": now_iso()})
            db.setdefault("errors", []).append({"projectId": project_id, "message": message, "at": now_iso()})
            save_db(db)
            return project


def export_project(project_id: str) -> dict:
    with DB_LOCK:
        project = find_item(load_db()["projects"], project_id)
        if project.get("status") not in ["Approved", "Ready for Preview", "Completed"]:
            raise ValueError("專案尚未準備好匯出")
    project = render_project(project_id, preview=False)
    write_export_package(project)
    return project


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
    return {"path": str(backup_path), "url": file_url(backup_path), "createdAt": now_iso()}


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
    return {"restored": True, "safetyBackup": safety}


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
        "V1_RELEASE_MANIFEST.md",
        "V1_RELEASE_NOTES.md",
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


def build_video_assets(project: dict, product: dict, preview: bool) -> dict:
    config = load_config()
    ffmpeg = config.get("ffmpegPath") or detect_ffmpeg()
    if not ffmpeg or not Path(ffmpeg).exists():
        raise RuntimeError("找不到 FFmpeg，無法輸出真正 MP4")
    output_dir = Path(project["outputDir"])
    frames_dir = Path(project["projectDir"]) / "frames"
    clips_dir = Path(project["projectDir"]) / "clips"
    output_dir.mkdir(parents=True, exist_ok=True)
    frames_dir.mkdir(parents=True, exist_ok=True)
    clips_dir.mkdir(parents=True, exist_ok=True)
    material_paths = [Path(m["path"]) for m in product.get("materials", []) if Path(m["path"]).exists()]
    if not material_paths:
        raise RuntimeError("找不到可用的商品照片")
    clip_paths = []
    for index, scene in enumerate(project["scenes"]):
        material = material_paths[index % len(material_paths)]
        frame_path = frames_dir / f"{scene['order']:02d}-{scene['id']}-v{scene['version']}.png"
        clip_path = clips_dir / f"{scene['order']:02d}-{scene['id']}-v{scene['version']}.mp4"
        create_scene_frame(material, frame_path, product, scene, project)
        make_clip(ffmpeg, frame_path, clip_path, int(scene["duration"]))
        clip_paths.append(clip_path)
    concat_path = Path(project["projectDir"]) / ("preview-concat.txt" if preview else "final-concat.txt")
    concat_path.write_text("".join([f"file '{path.as_posix()}'\n" for path in clip_paths]), encoding="utf-8")
    target = output_dir / ("preview.mp4" if preview else "final_video.mp4")
    run_ffmpeg([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_path), "-c", "copy", str(target)])
    srt_path = output_dir / "subtitles.srt"
    srt_path.write_text(build_srt(project["scenes"]), encoding="utf-8-sig")
    if not preview:
        subtitled = output_dir / "final_video_subtitled.mp4"
        shutil.copyfile(target, subtitled)
    return {
        "previewVideo": file_url(target) if preview else project.get("previewVideo"),
        "finalVideo": file_url(target) if not preview else project.get("finalVideo"),
        "subtitles": file_url(srt_path),
        "ffmpegPath": ffmpeg,
        "videoSpec": "1080x1920, MP4, H.264 via h264_mf when available, subtitles burned into frames",
    }


def create_scene_frame(material_path: Path, frame_path: Path, product: dict, scene: dict, project: dict) -> None:
    canvas = Image.new("RGB", FRAME_SIZE, "#f7f3ec")
    with Image.open(material_path) as source:
        source = source.convert("RGB")
        background = fit_cover(source, FRAME_SIZE).filter(ImageFilter.GaussianBlur(18))
        overlay = Image.new("RGB", FRAME_SIZE, "#ffffff")
        canvas = Image.blend(background, overlay, 0.36)
        product_img = fit_contain(source, (880, 900))
    draw = ImageDraw.Draw(canvas)
    product_x = (FRAME_SIZE[0] - product_img.width) // 2
    product_y = 430
    draw.rounded_rectangle(
        (product_x - 24, product_y - 24, product_x + product_img.width + 24, product_y + product_img.height + 24),
        radius=34,
        fill="#ffffff",
        outline="#d7c7ae",
        width=4,
    )
    canvas.paste(product_img, (product_x, product_y))
    title_font = get_font(54)
    purpose_font = get_font(34)
    subtitle_font = get_font(58)
    small_font = get_font(28)
    draw.text((80, 110), product["name"], fill="#17231f", font=title_font)
    draw.text((82, 178), scene["purpose"], fill="#8d5d3c", font=purpose_font)
    safe_box = (70, 1450, 1010, 1730)
    draw.rounded_rectangle(safe_box, radius=26, fill=(23, 35, 31))
    lines = wrap_text(draw, scene["subtitle"], subtitle_font, 880)
    y = safe_box[1] + 42
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=subtitle_font)
        draw.text(((FRAME_SIZE[0] - (bbox[2] - bbox[0])) // 2, y), line, fill="#ffffff", font=subtitle_font)
        y += 76
    if load_config().get("includeLogo", True):
        draw.rounded_rectangle((760, 1780, 1010, 1848), radius=12, fill="#245c4f")
        draw.text((790, 1796), "Temple AI Studio", fill="#ffffff", font=small_font)
    frame_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(frame_path)


def fit_cover(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    ratio = max(size[0] / img.width, size[1] / img.height)
    resized = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
    left = (resized.width - size[0]) // 2
    top = (resized.height - size[1]) // 2
    return resized.crop((left, top, left + size[0], top + size[1]))


def fit_contain(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    ratio = min(size[0] / img.width, size[1] / img.height)
    return img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)


def make_clip(ffmpeg: str, frame: Path, output: Path, duration: int) -> None:
    frames = max(FPS * duration, FPS * 2)
    vf = f"zoompan=z='min(zoom+0.0008,1.06)':d={frames}:s=1080x1920:fps={FPS},format=yuv420p"
    cmd = [
        ffmpeg,
        "-y",
        "-loop",
        "1",
        "-i",
        str(frame),
        "-vf",
        vf,
        "-frames:v",
        str(frames),
        "-r",
        str(FPS),
        "-an",
        "-c:v",
        "h264_mf",
        "-b:v",
        "5000k",
        str(output),
    ]
    try:
        run_ffmpeg(cmd)
    except RuntimeError:
        fallback = cmd.copy()
        fallback[fallback.index("h264_mf")] = "mpeg4"
        run_ffmpeg(fallback)


def run_ffmpeg(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "FFmpeg 執行失敗")


def build_srt(scenes: list[dict]) -> str:
    blocks = []
    for index, scene in enumerate(scenes, start=1):
        blocks.append(
            f"{index}\n{fmt_time(scene['start'])} --> {fmt_time(scene['end'])}\n{scene['subtitle']}\n"
        )
    return "\n".join(blocks)


def fmt_time(seconds: float) -> str:
    ms = int(round((seconds - int(seconds)) * 1000))
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_export_package(project: dict) -> None:
    output_dir = Path(project["outputDir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "narration.txt").write_text(project["script"], encoding="utf-8")
    (output_dir / "caption.txt").write_text(project["caption"], encoding="utf-8")
    (output_dir / "metadata.json").write_text(json.dumps(project["metadata"], ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "scenes.json").write_text(json.dumps(project["scenes"], ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "prompts.json").write_text(json.dumps(project["prompts"], ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "thumbnail_suggestion.txt").write_text(project["thumbnailSuggestion"], encoding="utf-8")
    product = find_item(load_db()["products"], project["productId"])
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


def json_response(handler: SimpleHTTPRequestHandler, payload, status: int = 200) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def read_json(handler: SimpleHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0") or "0")
    if length == 0:
        return {}
    raw = handler.rfile.read(length)
    return json.loads(raw.decode("utf-8"))


class AppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(APP_ROOT), **kwargs)

    def log_message(self, fmt, *args):
        sys.stdout.write("[%s] %s\n" % (now_iso(), fmt % args))

    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            path = parsed.path
            if path == "/api/health":
                return json_response(self, health_payload())
            if path == "/api/state":
                seed_demo_data()
                return json_response(self, {"db": load_db(), "config": load_config(), "health": health_payload()})
            if path.startswith("/api/files/"):
                return self.serve_data_file(path.removeprefix("/api/files/"))
            if path.startswith("/api/output-files/"):
                return self.serve_output_file(path.removeprefix("/api/output-files/"))
            if path == "/api/evidence/screenshots":
                return json_response(self, {"ok": True, **create_evidence_screenshots()})
            if path == "/api/release/package":
                return json_response(self, {"ok": True, **create_release_package()})
            if path.startswith("/api/export-package/"):
                project_id = path.rsplit("/", 1)[-1]
                project = find_item(load_db()["projects"], project_id)
                write_export_package(project)
                return json_response(self, {"ok": True, "outputDir": project["outputDir"]})
            return super().do_GET()
        except Exception as error:
            return json_response(self, {"ok": False, "message": user_error(error)}, 400)

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
                return json_response(self, {"ok": True, **add_materials(product_id, payload.get("files", []))})
            if path == "/api/projects":
                return json_response(self, {"ok": True, "project": create_project(payload)})
            if path == "/api/demo/run":
                return json_response(self, {"ok": True, "project": run_demo_project()})
            if path == "/api/backup":
                return json_response(self, {"ok": True, "backup": create_backup()})
            if path == "/api/restore":
                return json_response(self, {"ok": True, **restore_backup(payload.get("file", {}), payload.get("confirm", ""))})
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
            return json_response(self, {"ok": False, "message": user_error(error)}, 400)

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
            return json_response(self, {"ok": False, "message": user_error(error)}, 400)

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
            return json_response(self, {"ok": False, "message": user_error(error)}, 400)

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
    seed_demo_data()
    if "--smoke-test" in sys.argv:
        return smoke_test()
    host = "127.0.0.1"
    port = int(os.environ.get("TPVG_PORT", "4173"))
    server = ThreadingHTTPServer((host, port), AppHandler)
    print(f"Temple Product Video Generator V1 running at http://{host}:{port}")
    print(f"Data: {DATA_ROOT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Server stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
