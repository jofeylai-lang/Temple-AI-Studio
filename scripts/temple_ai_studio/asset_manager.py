from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image


ASSET_INDEX_SCHEMA = "temple-ai-studio.asset-index.v1"


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_metadata(path: Path) -> dict[str, Any]:
    payload: dict[str, Any] = {"sha256": sha256_file(path), "bytes": path.stat().st_size}
    try:
        with Image.open(path) as image:
            payload.update(
                {
                    "format": image.format,
                    "width": image.width,
                    "height": image.height,
                    "aspectRatio": round(image.width / image.height, 4) if image.height else None,
                    "mode": image.mode,
                }
            )
    except Exception as exc:
        payload["inspectionError"] = exc.__class__.__name__
    return payload


class AssetManager:
    def __init__(self, project_dir: Path, project_id: str):
        self.project_dir = Path(project_dir)
        self.project_id = project_id
        self.asset_root = self.project_dir / "assets"
        self.cache_root = self.project_dir / "cache"
        self.reference_root = self.asset_root / "references"
        self.generated_root = self.asset_root / "generated"
        self.index_path = self.asset_root / "asset-index.json"
        self.asset_root.mkdir(parents=True, exist_ok=True)
        self.cache_root.mkdir(parents=True, exist_ok=True)
        self.reference_root.mkdir(parents=True, exist_ok=True)
        self.generated_root.mkdir(parents=True, exist_ok=True)
        self.index = self._load_index()

    def _load_index(self) -> dict[str, Any]:
        if self.index_path.exists():
            return json.loads(self.index_path.read_text(encoding="utf-8"))
        return {
            "schema": ASSET_INDEX_SCHEMA,
            "projectId": self.project_id,
            "createdAt": now_iso(),
            "updatedAt": now_iso(),
            "assets": [],
        }

    def register(
        self,
        path: Path,
        asset_type: str,
        role: str,
        scene_id: str | None = None,
        provider: str | None = None,
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        path = Path(path).resolve()
        record = {
            "id": f"asset-{len(self.index['assets']) + 1:04d}",
            "projectId": self.project_id,
            "sceneId": scene_id,
            "type": asset_type,
            "role": role,
            "provider": provider,
            "source": source,
            "path": str(path),
            "fileName": path.name,
            "createdAt": now_iso(),
            "metadata": metadata or {},
        }
        if path.exists() and path.is_file():
            record["metadata"] = {**image_metadata(path), **record["metadata"]}
        self.index["assets"].append(record)
        self.index["updatedAt"] = now_iso()
        self.write()
        return record

    def register_product_assets(self, product: dict[str, Any]) -> list[dict[str, Any]]:
        records = []
        for item in product.get("materials", []) or []:
            path = Path(item.get("path", ""))
            if path.exists():
                records.append(
                    self.register(
                        path,
                        asset_type="reference-image",
                        role=item.get("role", "product-reference"),
                        source="product-library",
                        metadata={"productMaterialId": item.get("id"), "originalFileName": item.get("fileName")},
                    )
                )
        return records

    def write(self) -> Path:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(json.dumps(self.index, ensure_ascii=False, indent=2), encoding="utf-8")
        return self.index_path
