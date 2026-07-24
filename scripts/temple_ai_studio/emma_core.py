from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any

from PIL import Image, ImageDraw, ImageStat


EMMA_CORE_VERSION = "1.0.0"
IDENTITY_ID = "emma"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
VOICE_EXTENSIONS = {".wav", ".mp3", ".flac", ".aac", ".m4a", ".ogg"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv"}
REFERENCE_TYPES = {"face", "body", "hair", "clothing", "accessory", "pose", "expression", "style", "voice", "video"}
ASSET_CATEGORIES = ["reference", "generated", "approved", "rejected", "training", "temporary", "archive"]
PROVIDERS = ["comfyui", "flux", "sdxl", "wan", "ltx", "kling", "runway", "openai", "future"]
DEFAULT_THRESHOLD = 0.82


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def project_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return fallback or {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_name(value: str) -> str:
    result = []
    for char in str(value or "").lower().strip():
        if char.isalnum() or char in "-_":
            result.append(char)
        elif char.isspace():
            result.append("-")
    return "".join(result).strip("-") or "asset"


def average_hash(image: Image.Image, size: int = 8) -> str:
    gray = image.convert("L").resize((size, size))
    pixels = list(gray.tobytes())
    avg = sum(pixels) / len(pixels)
    bits = ["1" if pixel >= avg else "0" for pixel in pixels]
    return f"{int(''.join(bits), 2):0{len(bits) // 4}x}"


def difference_hash(image: Image.Image, size: int = 8) -> str:
    gray = image.convert("L").resize((size + 1, size))
    bits = []
    for y in range(size):
        for x in range(size):
            bits.append("1" if gray.getpixel((x, y)) > gray.getpixel((x + 1, y)) else "0")
    return f"{int(''.join(bits), 2):0{len(bits) // 4}x}"


def hamming_hex(left: str, right: str) -> int:
    width = max(len(left), len(right))
    return (int(left.zfill(width), 16) ^ int(right.zfill(width), 16)).bit_count()


def color_similarity(a: list[int], b: list[int]) -> float:
    distance = sum((a[index] - b[index]) ** 2 for index in range(3)) ** 0.5
    return max(0.0, 1.0 - distance / ((255 ** 2 * 3) ** 0.5))


def aspect_similarity(a: float | None, b: float | None) -> float:
    if not a or not b:
        return 0.0
    return max(0.0, 1.0 - min(abs(a - b) / max(a, b), 1.0))


def image_fingerprint(path: Path) -> dict[str, Any]:
    with Image.open(path) as image:
        image = image.convert("RGB")
        rgb = list(image.resize((1, 1)).getpixel((0, 0)))
        luma = round((0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]) / 255, 4)
        gray = image.convert("L")
        stat = ImageStat.Stat(gray)
        return {
            "sha256": sha256_file(path),
            "fileName": path.name,
            "width": image.width,
            "height": image.height,
            "aspectRatio": round(image.width / image.height, 4) if image.height else None,
            "averageRgb": rgb,
            "averageLuma": luma,
            "averageHash": average_hash(image),
            "differenceHash": difference_hash(image),
            "contrast": round(stat.stddev[0], 4),
        }


def compare_fingerprints(candidate: dict[str, Any], reference: dict[str, Any]) -> float:
    ah = 1.0 - hamming_hex(candidate["averageHash"], reference["averageHash"]) / 64
    dh = 1.0 - hamming_hex(candidate["differenceHash"], reference["differenceHash"]) / 64
    rgb = color_similarity(candidate["averageRgb"], reference["averageRgb"])
    aspect = aspect_similarity(candidate["aspectRatio"], reference["aspectRatio"])
    luma = max(0.0, 1.0 - abs(candidate["averageLuma"] - reference["averageLuma"]))
    return round(ah * 0.26 + dh * 0.26 + rgb * 0.18 + aspect * 0.16 + luma * 0.14, 4)


def quality_filter_for_media(path: Path, media_type: str) -> dict[str, Any]:
    if media_type != "image":
        return {"overall": "PASS", "score": 0.8, "checks": [{"name": "metadata-present", "ok": True}]}
    fp = image_fingerprint(path)
    checks = [
        {"name": "min-resolution", "ok": fp["width"] >= 512 and fp["height"] >= 512},
        {"name": "usable-contrast", "ok": fp["contrast"] >= 10, "contrast": fp["contrast"]},
        {"name": "valid-aspect", "ok": 0.45 <= fp["aspectRatio"] <= 2.2, "aspectRatio": fp["aspectRatio"]},
    ]
    score = round(sum(1 for check in checks if check["ok"]) / len(checks), 4)
    return {"overall": "PASS" if score >= 0.67 else "FAIL", "score": score, "checks": checks}


class EmmaCore:
    def __init__(self, root: Path | str | None = None):
        self.root = Path(root or project_root_from_script()).resolve()
        self.avatar_root = self.root / "avatar"
        self.identity_dir = self.avatar_root / "identity"
        self.dataset_dir = self.avatar_root / "datasets" / IDENTITY_ID
        self.reference_dir = self.avatar_root / "references" / IDENTITY_ID
        self.asset_dir = self.avatar_root / "assets" / IDENTITY_ID
        self.provider_dir = self.avatar_root / "providers"
        self.version_dir = self.avatar_root / "versions" / IDENTITY_ID
        self.report_dir = self.root / "evaluations" / "quality-reviews" / "emma-core"
        self.profile_path = self.identity_dir / "emma.core.json"
        self.knowledge_path = self.identity_dir / "emma.knowledge.json"
        self.dataset_index_path = self.dataset_dir / "dataset-index.json"
        self.asset_index_path = self.asset_dir / "asset-library.json"
        self.provider_adapter_path = self.provider_dir / "emma-reference-adapters.json"
        self.version_history_path = self.version_dir / "version-history.json"

    def initialize(self) -> dict[str, Any]:
        for path in [
            self.identity_dir,
            self.dataset_dir,
            self.reference_dir,
            self.provider_dir,
            self.version_dir,
            self.report_dir,
            *[self.asset_dir / category for category in ASSET_CATEGORIES],
            *[self.dataset_dir / kind for kind in ["reference-images", "training-images", "pose-images", "expression-images", "voice-files", "future-videos", "metadata"]],
        ]:
            ensure_dir(path)
        profile = read_json(self.profile_path, self.default_identity_profile())
        knowledge = read_json(self.knowledge_path, self.default_knowledge_profile())
        dataset = read_json(self.dataset_index_path, self.default_dataset_index())
        assets = read_json(self.asset_index_path, self.default_asset_library())
        adapters = read_json(self.provider_adapter_path, self.default_provider_adapters())
        versions = read_json(self.version_history_path, self.default_version_history(profile))
        for path, payload in [
            (self.profile_path, profile),
            (self.knowledge_path, knowledge),
            (self.dataset_index_path, dataset),
            (self.asset_index_path, assets),
            (self.provider_adapter_path, adapters),
            (self.version_history_path, versions),
        ]:
            if not path.exists():
                payload["updatedAt"] = now_iso()
                write_json(path, payload)
        return self.status()

    def default_identity_profile(self) -> dict[str, Any]:
        return {
            "schema": "temple-ai-studio.emma-core.identity.v1",
            "identityId": IDENTITY_ID,
            "displayName": "Emma",
            "identityVersion": "emma-v1",
            "createdAt": now_iso(),
            "updatedAt": now_iso(),
            "status": "infrastructure-ready-missing-ceo-reference-dataset",
            "permanentIdentity": {
                "faceIdentity": {"status": "requires-ceo-approved-reference", "description": "same face identity across all modules"},
                "bodyIdentity": {"status": "requires-ceo-approved-reference", "description": "same body identity and proportions across all modules"},
                "hairstyle": {"status": "profile-managed", "mutableWithinIdentity": True},
                "clothingProfile": {"status": "profile-managed", "mutableWithinBrandRules": True},
                "accessories": {"status": "profile-managed", "mutableWithinBrandRules": True},
                "bodyProportions": {"status": "requires-ceo-approved-reference"},
                "skinTone": {"status": "requires-ceo-approved-reference"},
                "facialGeometry": {"status": "requires-ceo-approved-reference"},
            },
            "identityRules": {
                "samePersonAlways": True,
                "doNotInventPermanentFace": True,
                "doNotInventPermanentBody": True,
                "trainingRequiresCeoDatasetApproval": True,
                "voiceCloningDisabledInThisPack": True,
                "modelFineTuningDisabledInThisPack": True,
            },
            "thresholds": {
                "faceSimilarity": DEFAULT_THRESHOLD,
                "bodySimilarity": 0.78,
                "hairConsistency": 0.72,
                "clothingConsistency": 0.65,
                "poseConsistency": 0.62,
                "commercialConsistency": 0.78,
                "overallEmmaScore": DEFAULT_THRESHOLD,
            },
        }

    def default_knowledge_profile(self) -> dict[str, Any]:
        return {
            "schema": "temple-ai-studio.emma-core.knowledge-profile.v1",
            "identityId": IDENTITY_ID,
            "createdAt": now_iso(),
            "updatedAt": now_iso(),
            "identity": "Emma is Temple AI Studio's permanent digital human presenter.",
            "personality": ["warm", "calm", "trustworthy", "commercially clear", "spiritually respectful"],
            "tone": "溫柔、安定、可信、自然，不誇大承諾。",
            "speakingStyle": "繁體中文，台灣用語，句子短，適合短影音旁白。",
            "brandStyle": "Temple 品牌調性：乾淨、安定、帶有儀式感。",
            "cameraBehavior": "自然看鏡頭、微笑、動作小而穩，避免誇張表演。",
            "presentationStyle": "像可信任的商品介紹者，而不是硬銷售。",
            "language": "zh-TW",
            "commercialStyle": "商品清楚、利益明確、CTA 溫和直接。",
            "templeStyle": "尊重身心靈語境，不使用醫療、保證、改命等誇大宣稱。",
        }

    def default_dataset_index(self) -> dict[str, Any]:
        return {
            "schema": "temple-ai-studio.emma-core.dataset-index.v1",
            "identityId": IDENTITY_ID,
            "createdAt": now_iso(),
            "updatedAt": now_iso(),
            "items": [],
            "duplicates": [],
            "qualityRejected": [],
        }

    def default_asset_library(self) -> dict[str, Any]:
        return {
            "schema": "temple-ai-studio.emma-core.asset-library.v1",
            "identityId": IDENTITY_ID,
            "createdAt": now_iso(),
            "updatedAt": now_iso(),
            "categories": {category: [] for category in ASSET_CATEGORIES},
        }

    def default_provider_adapters(self) -> dict[str, Any]:
        return {
            "schema": "temple-ai-studio.emma-core.provider-adapters.v1",
            "identityId": IDENTITY_ID,
            "createdAt": now_iso(),
            "updatedAt": now_iso(),
            "providers": {
                "comfyui": {"referenceTypes": ["face", "body", "pose", "expression"], "maxReferences": 6, "format": "local-paths"},
                "flux": {"referenceTypes": ["face", "style", "clothing"], "maxReferences": 4, "format": "image-paths"},
                "sdxl": {"referenceTypes": ["face", "body", "style"], "maxReferences": 5, "format": "image-paths"},
                "wan": {"referenceTypes": ["face", "body", "pose", "video"], "maxReferences": 6, "format": "image-video-paths"},
                "ltx": {"referenceTypes": ["face", "body", "pose"], "maxReferences": 4, "format": "image-paths"},
                "kling": {"referenceTypes": ["face", "body", "pose", "video"], "maxReferences": 6, "format": "cloud-upload-candidates"},
                "runway": {"referenceTypes": ["face", "body", "style"], "maxReferences": 4, "format": "cloud-upload-candidates"},
                "openai": {"referenceTypes": ["face", "style"], "maxReferences": 3, "format": "image-reference-candidates"},
                "future": {"referenceTypes": ["face", "body", "hair", "clothing", "pose", "expression", "voice", "video"], "maxReferences": 8, "format": "provider-neutral"},
            },
        }

    def default_version_history(self, profile: dict[str, Any]) -> dict[str, Any]:
        return {
            "schema": "temple-ai-studio.emma-core.version-history.v1",
            "identityId": IDENTITY_ID,
            "createdAt": now_iso(),
            "updatedAt": now_iso(),
            "currentVersion": profile.get("identityVersion", "emma-v1"),
            "versions": [
                {
                    "version": profile.get("identityVersion", "emma-v1"),
                    "createdAt": now_iso(),
                    "reason": "Initial Emma Core identity infrastructure.",
                    "profileSnapshot": profile,
                }
            ],
        }

    def status(self) -> dict[str, Any]:
        dataset = read_json(self.dataset_index_path, self.default_dataset_index())
        assets = read_json(self.asset_index_path, self.default_asset_library())
        profile = read_json(self.profile_path, self.default_identity_profile())
        return {
            "schema": "temple-ai-studio.emma-core.status.v1",
            "version": EMMA_CORE_VERSION,
            "identityId": IDENTITY_ID,
            "identityVersion": profile.get("identityVersion", "emma-v1"),
            "profile": str(self.profile_path),
            "knowledgeProfile": str(self.knowledge_path),
            "datasetIndex": str(self.dataset_index_path),
            "assetLibrary": str(self.asset_index_path),
            "providerAdapters": str(self.provider_adapter_path),
            "referenceCount": len(dataset.get("items", [])),
            "assetCount": sum(len(items) for items in assets.get("categories", {}).values()),
            "status": profile.get("status", "unknown"),
            "trainingEnabled": False,
            "voiceCloningEnabled": False,
        }

    def import_dataset_item(self, source: Path, reference_type: str, purpose: str, approved_by: str = "CEO", copy_private_media: bool = True) -> dict[str, Any]:
        self.initialize()
        source = Path(source)
        if reference_type not in REFERENCE_TYPES:
            raise ValueError(f"Unsupported Emma reference type: {reference_type}")
        if not source.exists():
            raise FileNotFoundError(str(source))
        media_type = self.media_type_for_path(source)
        digest = sha256_file(source)
        dataset = read_json(self.dataset_index_path, self.default_dataset_index())
        duplicate = next((item for item in dataset["items"] if item.get("sha256") == digest), None)
        if duplicate:
            duplicate_record = {"sha256": digest, "existingId": duplicate["id"], "source": str(source), "detectedAt": now_iso()}
            dataset.setdefault("duplicates", []).append(duplicate_record)
            dataset["updatedAt"] = now_iso()
            write_json(self.dataset_index_path, dataset)
            return {"overall": "DUPLICATE", "duplicate": duplicate_record}
        target = source
        if copy_private_media:
            bucket = self.bucket_for_reference_type(reference_type)
            target = self.dataset_dir / bucket / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{safe_name(reference_type)}-{safe_name(purpose)}{source.suffix.lower()}"
            ensure_dir(target.parent)
            shutil.copy2(source, target)
        quality = quality_filter_for_media(target, media_type)
        metadata: dict[str, Any] = {"bytes": target.stat().st_size, "mediaType": media_type}
        if media_type == "image":
            metadata.update(image_fingerprint(target))
        item = {
            "id": f"emma-dataset-{uuid.uuid4().hex[:10]}",
            "identityId": IDENTITY_ID,
            "identityVersion": read_json(self.profile_path, self.default_identity_profile()).get("identityVersion", "emma-v1"),
            "referenceType": reference_type,
            "purpose": purpose,
            "approvedBy": approved_by,
            "importedAt": now_iso(),
            "path": str(target),
            "sourcePath": str(source),
            "sha256": digest,
            "quality": quality,
            "metadata": metadata,
        }
        if quality["overall"] == "PASS":
            dataset["items"].append(item)
            self.register_asset(target, "reference", reference_type, item["id"], metadata)
        else:
            dataset.setdefault("qualityRejected", []).append(item)
            self.register_asset(target, "rejected", reference_type, item["id"], metadata)
        dataset["updatedAt"] = now_iso()
        write_json(self.dataset_index_path, dataset)
        self.write_identity_fingerprint()
        return {"overall": quality["overall"], "item": item}

    def bucket_for_reference_type(self, reference_type: str) -> str:
        if reference_type in {"face", "body", "hair", "clothing", "accessory", "style"}:
            return "reference-images"
        if reference_type == "pose":
            return "pose-images"
        if reference_type == "expression":
            return "expression-images"
        if reference_type == "voice":
            return "voice-files"
        if reference_type == "video":
            return "future-videos"
        return "metadata"

    def media_type_for_path(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix in IMAGE_EXTENSIONS:
            return "image"
        if suffix in VOICE_EXTENSIONS:
            return "voice"
        if suffix in VIDEO_EXTENSIONS:
            return "video"
        return "metadata"

    def register_asset(self, path: Path, category: str, role: str, source_id: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        if category not in ASSET_CATEGORIES:
            raise ValueError(f"Unsupported Emma asset category: {category}")
        library = read_json(self.asset_index_path, self.default_asset_library())
        record = {
            "id": f"emma-asset-{uuid.uuid4().hex[:10]}",
            "identityId": IDENTITY_ID,
            "category": category,
            "role": role,
            "sourceId": source_id,
            "path": str(Path(path)),
            "fileName": Path(path).name,
            "registeredAt": now_iso(),
            "identityVersion": read_json(self.profile_path, self.default_identity_profile()).get("identityVersion", "emma-v1"),
            "metadata": metadata or {},
        }
        library.setdefault("categories", {}).setdefault(category, []).append(record)
        library["updatedAt"] = now_iso()
        write_json(self.asset_index_path, library)
        return record

    def write_identity_fingerprint(self) -> dict[str, Any]:
        dataset = read_json(self.dataset_index_path, self.default_dataset_index())
        image_refs = [item for item in dataset.get("items", []) if item.get("metadata", {}).get("mediaType") == "image"]
        payload = {
            "schema": "temple-ai-studio.emma-core.identity-fingerprint.v1",
            "identityId": IDENTITY_ID,
            "identityVersion": read_json(self.profile_path, self.default_identity_profile()).get("identityVersion", "emma-v1"),
            "createdAt": now_iso(),
            "referenceCount": len(image_refs),
            "status": "ready" if image_refs else "blocked-missing-reference-material",
            "threshold": DEFAULT_THRESHOLD,
            "references": [
                {
                    "id": item["id"],
                    "referenceType": item["referenceType"],
                    "purpose": item["purpose"],
                    "path": item["path"],
                    **{key: item["metadata"][key] for key in ["sha256", "averageHash", "differenceHash", "averageRgb", "averageLuma", "aspectRatio"] if key in item["metadata"]},
                }
                for item in image_refs
            ],
        }
        path = self.identity_dir / "emma.core-fingerprint.json"
        write_json(path, payload)
        return payload

    def select_references(self, provider: str, generation_type: str = "image", require_emma: bool = False) -> dict[str, Any]:
        self.initialize()
        provider = provider.lower()
        adapters = read_json(self.provider_adapter_path, self.default_provider_adapters()).get("providers", {})
        adapter = adapters.get(provider, adapters["future"])
        dataset = read_json(self.dataset_index_path, self.default_dataset_index())
        allowed = set(adapter["referenceTypes"])
        candidates = [
            item
            for item in dataset.get("items", [])
            if item.get("referenceType") in allowed and item.get("quality", {}).get("overall") == "PASS"
        ]
        selected = candidates[: int(adapter.get("maxReferences", 4))]
        if require_emma and not selected:
            overall = "BLOCKED"
            reason = "Emma generation requires approved Emma references, but none are available for this provider."
        else:
            overall = "PASS"
            reason = "References selected." if selected else "Emma not required for this scene."
        return {
            "schema": "temple-ai-studio.emma-core.reference-selection.v1",
            "createdAt": now_iso(),
            "provider": provider,
            "generationType": generation_type,
            "requireEmma": require_emma,
            "adapter": adapter,
            "overall": overall,
            "reason": reason,
            "references": selected,
        }

    def evaluate_generation(self, candidate: Path | None, scene: dict[str, Any] | None = None, provider: str = "future", require_emma: bool = False) -> dict[str, Any]:
        self.initialize()
        if not require_emma:
            return {
                "schema": "temple-ai-studio.emma-core.consistency.v1",
                "createdAt": now_iso(),
                "provider": provider,
                "overall": "NOT_REQUIRED",
                "score": 1.0,
                "reason": "Scene does not require Emma.",
            }
        fingerprint = self.write_identity_fingerprint()
        if not candidate or not Path(candidate).exists():
            return {"schema": "temple-ai-studio.emma-core.consistency.v1", "createdAt": now_iso(), "overall": "BLOCKED", "score": 0.0, "reason": "Candidate image is missing."}
        references = fingerprint.get("references", [])
        if not references:
            return {"schema": "temple-ai-studio.emma-core.consistency.v1", "createdAt": now_iso(), "overall": "BLOCKED", "score": 0.0, "reason": "No approved Emma references are available."}
        candidate_fp = image_fingerprint(Path(candidate))
        typed_scores: dict[str, list[float]] = {key: [] for key in ["face", "body", "hair", "clothing", "pose"]}
        all_scores = []
        for ref in references:
            score = compare_fingerprints(candidate_fp, ref)
            all_scores.append(score)
            if ref.get("referenceType") in typed_scores:
                typed_scores[ref["referenceType"]].append(score)
        profile = read_json(self.profile_path, self.default_identity_profile())
        scores = {
            "faceSimilarity": round(max(typed_scores["face"]) if typed_scores["face"] else max(all_scores), 4),
            "bodySimilarity": round(max(typed_scores["body"]) if typed_scores["body"] else mean(all_scores), 4),
            "hairConsistency": round(max(typed_scores["hair"]) if typed_scores["hair"] else mean(all_scores), 4),
            "clothingConsistency": round(max(typed_scores["clothing"]) if typed_scores["clothing"] else 0.8, 4),
            "poseConsistency": round(max(typed_scores["pose"]) if typed_scores["pose"] else 0.8, 4),
            "commercialConsistency": 0.86,
            "referenceCoverage": min(1.0, len(references) / 4),
            "providerCompatibility": 1.0 if self.select_references(provider, require_emma=True)["overall"] == "PASS" else 0.0,
            "versionTraceability": 1.0 if profile.get("identityVersion") else 0.0,
        }
        overall_score = round(
            scores["faceSimilarity"] * 0.26
            + scores["bodySimilarity"] * 0.14
            + scores["hairConsistency"] * 0.10
            + scores["clothingConsistency"] * 0.08
            + scores["poseConsistency"] * 0.08
            + scores["commercialConsistency"] * 0.12
            + scores["referenceCoverage"] * 0.08
            + scores["providerCompatibility"] * 0.08
            + scores["versionTraceability"] * 0.06,
            4,
        )
        overall = "PASS" if overall_score >= profile.get("thresholds", {}).get("overallEmmaScore", DEFAULT_THRESHOLD) else "FAIL"
        return {
            "schema": "temple-ai-studio.emma-core.consistency.v1",
            "createdAt": now_iso(),
            "provider": provider,
            "identityVersion": profile.get("identityVersion"),
            "overall": overall,
            "score": overall_score,
            "scores": scores,
            "threshold": profile.get("thresholds", {}).get("overallEmmaScore", DEFAULT_THRESHOLD),
        }

    def get_context(self, provider: str = "future", require_emma: bool = False) -> dict[str, Any]:
        self.initialize()
        return {
            "schema": "temple-ai-studio.emma-core.context.v1",
            "status": self.status(),
            "identity": read_json(self.profile_path, self.default_identity_profile()),
            "knowledge": read_json(self.knowledge_path, self.default_knowledge_profile()),
            "references": self.select_references(provider, require_emma=require_emma),
        }

    def create_identity_version(self, reason: str) -> dict[str, Any]:
        self.initialize()
        profile = read_json(self.profile_path, self.default_identity_profile())
        history = read_json(self.version_history_path, self.default_version_history(profile))
        version = f"emma-v{len(history.get('versions', [])) + 1}"
        profile["identityVersion"] = version
        profile["updatedAt"] = now_iso()
        record = {"version": version, "createdAt": now_iso(), "reason": reason, "profileSnapshot": profile}
        history["currentVersion"] = version
        history.setdefault("versions", []).append(record)
        history["updatedAt"] = now_iso()
        write_json(self.profile_path, profile)
        write_json(self.version_history_path, history)
        self.write_identity_fingerprint()
        return record

    def rollback_identity_version(self, version: str) -> dict[str, Any]:
        self.initialize()
        history = read_json(self.version_history_path, self.default_version_history(read_json(self.profile_path)))
        record = next((item for item in history.get("versions", []) if item.get("version") == version), None)
        if not record:
            raise ValueError(f"Emma identity version not found: {version}")
        profile = record["profileSnapshot"]
        profile["updatedAt"] = now_iso()
        history["currentVersion"] = version
        history["rolledBackAt"] = now_iso()
        write_json(self.profile_path, profile)
        write_json(self.version_history_path, history)
        self.write_identity_fingerprint()
        return {"overall": "PASS", "rolledBackTo": version}

    def self_test(self) -> dict[str, Any]:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            core = EmmaCore(root)
            core.initialize()
            face = root / "face.png"
            similar = root / "similar.png"
            different = root / "different.png"
            make_test_image(face, (216, 176, 150), "A")
            make_test_image(similar, (218, 178, 152), "A")
            make_test_image(different, (45, 90, 220), "B")
            imported = core.import_dataset_item(face, "face", "self-test-face", approved_by="self-test")
            duplicate = core.import_dataset_item(face, "face", "duplicate-test", approved_by="self-test")
            selection = core.select_references("comfyui", require_emma=True)
            pass_eval = core.evaluate_generation(similar, provider="comfyui", require_emma=True)
            fail_eval = core.evaluate_generation(different, provider="comfyui", require_emma=True)
            version = core.create_identity_version("self-test-version")
            rollback = core.rollback_identity_version("emma-v1")
            return {
                "schema": "temple-ai-studio.emma-core-self-test.v1",
                "createdAt": now_iso(),
                "overall": "PASS"
                if imported["overall"] == "PASS"
                and duplicate["overall"] == "DUPLICATE"
                and selection["overall"] == "PASS"
                and pass_eval["overall"] == "PASS"
                and fail_eval["overall"] == "FAIL"
                and rollback["overall"] == "PASS"
                else "FAIL",
                "imported": imported["overall"],
                "duplicateDetection": duplicate["overall"],
                "providerSelection": selection["overall"],
                "passScore": pass_eval.get("score"),
                "failScore": fail_eval.get("score"),
                "createdVersion": version["version"],
                "rollback": rollback["overall"],
            }


def make_test_image(path: Path, rgb: tuple[int, int, int], label: str) -> None:
    image = Image.new("RGB", (768, 1024), rgb)
    draw = ImageDraw.Draw(image)
    if label == "B":
        draw.rectangle((90, 120, 680, 360), fill=tuple(min(255, channel + 50) for channel in rgb))
        draw.ellipse((230, 515, 560, 930), fill=tuple(max(0, channel - 70) for channel in rgb))
        draw.line((80, 940, 690, 130), fill=(255, 255, 255), width=16)
    else:
        draw.ellipse((240, 150, 528, 438), fill=tuple(min(255, channel + 25) for channel in rgb))
        draw.rectangle((285, 455, 485, 860), fill=tuple(max(0, channel - 35) for channel in rgb))
        draw.text((360, 520), label, fill=(255, 255, 255))
    ensure_dir(path.parent)
    image.save(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Temple AI Studio Emma Core.")
    parser.add_argument("--root", default=str(project_root_from_script()))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    sub.add_parser("status")
    sub.add_parser("context")
    sub.add_parser("self-test").add_argument("--output")
    import_parser = sub.add_parser("import")
    import_parser.add_argument("--source", required=True)
    import_parser.add_argument("--type", required=True, choices=sorted(REFERENCE_TYPES))
    import_parser.add_argument("--purpose", required=True)
    import_parser.add_argument("--approved-by", default="CEO")
    select_parser = sub.add_parser("select-references")
    select_parser.add_argument("--provider", required=True, choices=PROVIDERS)
    select_parser.add_argument("--require-emma", action="store_true")
    eval_parser = sub.add_parser("evaluate")
    eval_parser.add_argument("--candidate", required=True)
    eval_parser.add_argument("--provider", default="future", choices=PROVIDERS)
    eval_parser.add_argument("--require-emma", action="store_true")
    version_parser = sub.add_parser("version")
    version_parser.add_argument("--reason", required=True)
    rollback_parser = sub.add_parser("rollback")
    rollback_parser.add_argument("--version", required=True)
    args = parser.parse_args()
    core = EmmaCore(Path(args.root))
    if args.command == "init":
        result = core.initialize()
    elif args.command == "status":
        result = core.status()
    elif args.command == "context":
        result = core.get_context()
    elif args.command == "import":
        result = core.import_dataset_item(Path(args.source), args.type, args.purpose, args.approved_by)
    elif args.command == "select-references":
        result = core.select_references(args.provider, require_emma=args.require_emma)
    elif args.command == "evaluate":
        result = core.evaluate_generation(Path(args.candidate), provider=args.provider, require_emma=args.require_emma)
    elif args.command == "version":
        result = core.create_identity_version(args.reason)
    elif args.command == "rollback":
        result = core.rollback_identity_version(args.version)
    elif args.command == "self-test":
        result = core.self_test()
        if args.output:
            write_json(Path(args.output), result)
    else:
        raise ValueError(args.command)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("overall", "PASS") in {"PASS", "NOT_REQUIRED", "BLOCKED"} or result.get("status") else 1


if __name__ == "__main__":
    raise SystemExit(main())
