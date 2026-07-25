from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from temple_ai_studio.image_pipeline import run_image_pipeline
from temple_ai_studio.script_engine import generate_video_script_package
from temple_ai_studio.video_intelligence import run_video_generation_pipeline


REQUEST = "Emma 介紹一項泰國宗教商品，15 秒，直式短影音。"
PROJECT_ID = "project-20260725-quality-rebuild"


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def make_contact_sheet(ffmpeg: Path, video: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(ffmpeg),
        "-y",
        "-i",
        str(video),
        "-vf",
        "fps=0.4,scale=270:-1:flags=lanczos,tile=3x4",
        "-frames:v",
        "1",
        str(output),
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Contact sheet failed: {result.stderr[-2000:]}")


def root_source_counts(report: dict) -> dict[str, int]:
    roots = [
        str(item.get("sourceImage", ""))
        for item in report.get("generatedImages", [])
        if item and item.get("sourceImage")
    ]
    return dict(Counter(roots))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--production-root", required=True)
    parser.add_argument("--application-data", required=True)
    parser.add_argument("--ffmpeg", required=True)
    parser.add_argument("--old-video", required=True)
    parser.add_argument("--old-project-dir", required=True)
    args = parser.parse_args()

    production_root = Path(args.production_root).resolve()
    application_data = Path(args.application_data).resolve()
    ffmpeg = Path(args.ffmpeg).resolve()
    old_video = Path(args.old_video).resolve()
    old_project_dir = Path(args.old_project_dir).resolve()
    project_dir = application_data / "projects" / PROJECT_ID
    evidence_root = application_data / "evidence" / "quality-rebuild"
    new_root = evidence_root / "new"
    output_dir = new_root
    project_dir.mkdir(parents=True, exist_ok=True)
    new_root.mkdir(parents=True, exist_ok=True)

    product = {
        "id": "",
        "name": "泰國祝福佛牌墜飾",
        "category": "泰國宗教商品",
        "description": REQUEST,
        "sellingPoint": "小巧細緻、方便日常配戴或珍藏，購買前可先了解來源與商品細節。",
        "spiritualInfo": "承載祝福與自我提醒的文化意涵，應以尊重信仰與來源的方式認識。",
        "targetAudience": "想了解泰國祝福飾品與文化意涵的顧客",
        "materials": [],
    }
    project = generate_video_script_package(
        product,
        {
            "requirement": REQUEST,
            "platform": "Instagram Reels",
            "duration": 30,
        },
        PROJECT_ID,
    )
    project.update(
        {
            "id": PROJECT_ID,
            "mode": "text-only",
            "projectDir": str(project_dir),
            "outputDir": str(output_dir),
            "status": "quality-rebuild-acceptance",
        }
    )
    write_json(project_dir / "acceptance-request.json", {"request": REQUEST})
    write_json(project_dir / "acceptance-product.json", product)
    write_json(project_dir / "acceptance-project-before-generation.json", project)

    visual = run_image_pipeline(
        project,
        product,
        project_dir,
        emma_root=production_root,
    )
    recovered_wan = next(
        iter(
            sorted(
                (
                    Path.home()
                    / "AppData"
                    / "Local"
                    / "Comfy-Desktop"
                    / "ComfyUI-Shared"
                    / "output"
                ).glob(f"{PROJECT_ID}-scene-03-product-features-wan22_*.mp4"),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
        ),
        None,
    )
    if recovered_wan:
        recovered_target = project_dir / "vgen" / "s3" / "wan22-recovered.mp4"
        recovered_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(recovered_wan, recovered_target)
        wan_scene = next(
            scene
            for scene in project["scenes"]
            if scene.get("purpose") == "Hook"
        )
        wan_scene["generatedVideoPath"] = str(recovered_target)
        wan_scene["videoProvenance"] = {
            "provider": "wan22-ti2v-local",
            "workflow": str(production_root / "workflows" / "wan22-ti2v-production.json"),
            "sourceImage": str(
                production_root
                / "emma"
                / "intake"
                / "synthetic-seed-v1"
                / "01_identity_anchors"
                / "emma_anchor_03_product_hold_white_tee.png"
            ),
            "artifact": str(recovered_target),
            "provenance": "real-production-recovered-after-windows-path-fix",
        }
    source_offsets = [0.6, 1.0, 0.8, 0.7, 0.3]
    video_scene_index = 0
    for scene in project["scenes"]:
        if scene.get("sourceVideoPath"):
            scene["sourceVideoStartSeconds"] = source_offsets[video_scene_index]
            video_scene_index += 1
    video = run_video_generation_pipeline(
        project,
        product,
        output_dir,
        project_dir,
        ffmpeg,
        preview=True,
        production_root=production_root,
    )
    new_video = Path(video["outputVideo"])
    if not new_video.is_file():
        raise RuntimeError("The rebuilt acceptance video was not created.")

    old_copy = evidence_root / "old" / "rejected-preview.mp4"
    old_copy.parent.mkdir(parents=True, exist_ok=True)
    if old_video != old_copy:
        shutil.copy2(old_video, old_copy)
    make_contact_sheet(ffmpeg, old_copy, evidence_root / "old" / "contact-sheet.jpg")
    make_contact_sheet(ffmpeg, new_video, new_root / "contact-sheet.jpg")

    old_visual = json.loads(
        (old_project_dir / "visual-pipeline-report.json").read_text(encoding="utf-8-sig")
    )
    old_video_report = json.loads(
        (old_project_dir / "video-intelligence-preview-report.json").read_text(
            encoding="utf-8-sig"
        )
    )
    corrected_old_quality_path = (
        evidence_root / "old" / "frame-editorial-quality-current.json"
    )
    corrected_old_quality = (
        json.loads(corrected_old_quality_path.read_text(encoding="utf-8-sig"))
        if corrected_old_quality_path.is_file()
        else {}
    )
    comparison = {
        "schema": "temple-ai-studio.video-quality-rebuild-acceptance.v1",
        "createdAt": datetime.now().replace(microsecond=0).isoformat(),
        "request": REQUEST,
        "old": {
            "video": str(old_copy),
            "provider": old_video_report.get("provider"),
            "reportedScore": old_video_report.get("quality", {}).get("score"),
            "reportedOverall": old_video_report.get("quality", {}).get("overall"),
            "rootSourceCounts": root_source_counts(old_visual),
            "contactSheet": str(evidence_root / "old" / "contact-sheet.jpg"),
            "correctedEditorialOverall": corrected_old_quality.get("overall"),
            "correctedEditorialMetrics": corrected_old_quality.get("editorial"),
            "correctedMotionMetrics": corrected_old_quality.get("motion"),
            "correctedCommercialVisualScore": corrected_old_quality.get(
                "commercialVisualScore"
            ),
            "correctedFailedChecks": [
                name
                for name, passed in corrected_old_quality.get("checks", {}).items()
                if not passed
            ],
        },
        "new": {
            "video": str(new_video),
            "provider": video.get("provider"),
            "score": video.get("quality", {}).get("score"),
            "overall": video.get("quality", {}).get("overall"),
            "editorialMetrics": video.get("quality", {}).get("editorialMetrics"),
            "frameQuality": video.get("frameQuality"),
            "contactSheet": str(new_root / "contact-sheet.jpg"),
            "voiceProfileId": video.get("narration", {}).get("voiceProfileId"),
            "generatedVideoEvidence": video.get("generatedVideoEvidence", []),
        },
        "sceneProvenance": [
            {
                "sceneId": item["sceneId"],
                "purpose": item.get("purpose"),
                "rootSource": item.get("provenance", {}).get("rootSource"),
                "renderSource": item.get("provenance", {}).get("renderSource"),
                "renderMode": item.get("provenance", {}).get("renderMode"),
                "motionSignature": item.get("render", {}).get("motionSignature"),
            }
            for item in video.get("sceneReports", [])
        ],
    }
    write_json(new_root / "comparison.json", comparison)
    write_json(project_dir / "acceptance-project-after-generation.json", project)
    print(json.dumps(comparison, ensure_ascii=False, indent=2))
    return 0 if video.get("quality", {}).get("overall") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
