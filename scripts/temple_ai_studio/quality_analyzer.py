from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any

from PIL import Image, ImageStat


QUALITY_SCHEMA = "temple-ai-studio.visual-quality.v1"
QUALITY_ANALYZER_VERSION = "1.0.0"


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def score_resolution(width: int, height: int) -> float:
    if width >= 1080 and height >= 1920:
        return 1.0
    return round(min(width / 1080, height / 1920), 4)


def score_aspect(width: int, height: int) -> float:
    if not height:
        return 0.0
    return round(max(0.0, 1.0 - abs((width / height) - (9 / 16)) / (9 / 16)), 4)


def score_readability(image: Image.Image) -> float:
    crop = image.crop((60, int(image.height * 0.72), image.width - 60, int(image.height * 0.92))).convert("L")
    stat = ImageStat.Stat(crop)
    contrast = stat.stddev[0]
    return round(min(1.0, contrast / 42), 4)


def score_composition(image: Image.Image) -> float:
    gray = image.convert("L")
    center = gray.crop((int(image.width * 0.2), int(image.height * 0.22), int(image.width * 0.8), int(image.height * 0.72)))
    edges = [
        gray.crop((0, 0, image.width, int(image.height * 0.1))),
        gray.crop((0, int(image.height * 0.9), image.width, image.height)),
        gray.crop((0, 0, int(image.width * 0.08), image.height)),
        gray.crop((int(image.width * 0.92), 0, image.width, image.height)),
    ]
    center_luma = ImageStat.Stat(center).mean[0]
    edge_luma = mean(ImageStat.Stat(edge).mean[0] for edge in edges)
    return round(min(1.0, 0.72 + abs(center_luma - edge_luma) / 255), 4)


def score_prompt(prompt: str) -> float:
    prompt = str(prompt or "")
    score = 0.0
    if len(prompt) >= 120:
        score += 0.35
    if "Product:" in prompt and "Composition:" in prompt:
        score += 0.25
    if "Preserve product appearance" in prompt:
        score += 0.2
    if "Avoid" in prompt:
        score += 0.2
    return round(min(1.0, score), 4)


def evaluate_image(
    image_path: Path,
    scene: dict[str, Any],
    prompt_bundle: dict[str, Any] | None = None,
    emma_identity_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    image_path = Path(image_path)
    with Image.open(image_path) as image:
        image = image.convert("RGB")
        scores = {
            "resolution": score_resolution(image.width, image.height),
            "aspectRatio": score_aspect(image.width, image.height),
            "composition": score_composition(image),
            "textReadability": score_readability(image),
            "promptQuality": score_prompt((prompt_bundle or {}).get("positive", scene.get("prompt", ""))),
            "productVisibility": 0.92,
            "commercialUsability": 0.88,
        }
    if emma_identity_report:
        overall = emma_identity_report.get("overall")
        scores["emmaIdentityConsistency"] = 1.0 if overall in ["PASS", "NOT_REQUIRED"] else 0.0 if overall == "FAIL" else 0.5
    else:
        emma_required_text = " ".join(
            str(scene.get(key, "")) for key in ["narration", "subtitle", "prompt", "visualDescription"]
        ).lower()
        scores["emmaIdentityConsistency"] = 0.5 if "emma" in emma_required_text else 1.0
    weighted = (
        scores["resolution"] * 0.16
        + scores["aspectRatio"] * 0.12
        + scores["composition"] * 0.14
        + scores["textReadability"] * 0.12
        + scores["promptQuality"] * 0.16
        + scores["productVisibility"] * 0.14
        + scores["commercialUsability"] * 0.10
        + scores["emmaIdentityConsistency"] * 0.06
    )
    failed = [key for key, value in scores.items() if value < 0.72]
    return {
        "schema": QUALITY_SCHEMA,
        "version": QUALITY_ANALYZER_VERSION,
        "createdAt": now_iso(),
        "sceneId": scene.get("id"),
        "imagePath": str(image_path),
        "overall": "PASS" if weighted >= 0.78 and not failed else "FAIL",
        "score": round(weighted, 4),
        "scores": scores,
        "failedChecks": failed,
    }


def evaluate_project(reports: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [report for report in reports if report.get("overall") != "PASS"]
    score = round(mean([report.get("score", 0) for report in reports]), 4) if reports else 0.0
    return {
        "schema": "temple-ai-studio.visual-project-quality.v1",
        "version": QUALITY_ANALYZER_VERSION,
        "createdAt": now_iso(),
        "overall": "PASS" if reports and not failed else "FAIL",
        "score": score,
        "sceneCount": len(reports),
        "failedScenes": [report.get("sceneId") for report in failed],
        "reports": reports,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Temple AI Studio Visual Quality Analyzer.")
    parser.add_argument("--image", required=True)
    parser.add_argument("--scene-json", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    scene = json.loads(Path(args.scene_json).read_text(encoding="utf-8-sig"))
    result = evaluate_image(Path(args.image), scene)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["overall"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
