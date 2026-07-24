from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from shutil import which


REQUIRED_EXPORT_FILES = [
    "final_video.mp4",
    "subtitles.srt",
    "narration.txt",
    "caption.txt",
    "metadata.json",
    "scenes.json",
    "prompts.json",
    "thumbnail_suggestion.txt",
    "materials_used.txt",
]

MOJIBAKE_HINTS = ["�", "甇", "銝", "摰", "隢", "雿", "鞈", "撱箇", "蝣箏", "憭望"]


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def detect_ffmpeg(explicit: str | None) -> str | None:
    candidates = [
        explicit,
        os.environ.get("TEMPLE_FFMPEG_PATH"),
        which("ffmpeg"),
        r"C:\Program Files\Softdeluxe\Free Download Manager\ffmpeg.exe",
        r"C:\ffmpeg\bin\ffmpeg.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    return None


def run_ffmpeg_decode(ffmpeg: str, video: Path) -> dict:
    cmd = [ffmpeg, "-hide_banner", "-i", str(video), "-f", "null", "NUL"]
    started = datetime.now()
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    elapsed = (datetime.now() - started).total_seconds()
    output = "\n".join([result.stdout, result.stderr])
    return {
        "ok": result.returncode == 0,
        "elapsedSeconds": round(elapsed, 3),
        "returnCode": result.returncode,
        "metadata": parse_ffmpeg_metadata(output),
        "errorTail": output[-2000:] if result.returncode else "",
    }


def parse_ffmpeg_metadata(output: str) -> dict:
    duration = None
    duration_match = re.search(r"Duration:\s*([0-9:.]+)", output)
    if duration_match:
        duration = duration_match.group(1)

    video_line = ""
    for line in output.splitlines():
        if "Video:" in line:
            video_line = line.strip()
            break

    size = None
    size_match = re.search(r"(\d{3,5})x(\d{3,5})", video_line)
    if size_match:
        size = {"width": int(size_match.group(1)), "height": int(size_match.group(2))}

    fps = None
    fps_match = re.search(r"([0-9.]+)\s*fps", video_line)
    if fps_match:
        fps = float(fps_match.group(1))

    codec = None
    codec_match = re.search(r"Video:\s*([^,\n]+)", video_line)
    if codec_match:
        codec = codec_match.group(1).strip()

    return {
        "duration": duration,
        "codec": codec,
        "size": size,
        "fps": fps,
        "videoLine": video_line,
    }


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def check_json(path: Path) -> dict:
    try:
        json.loads(read_text(path))
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def check_text_quality(path: Path) -> dict:
    text = read_text(path)
    hints = [hint for hint in MOJIBAKE_HINTS if hint in text]
    return {
        "ok": bool(text.strip()) and not hints,
        "characters": len(text),
        "mojibakeHints": hints,
    }


def evaluate_export(export_dir: Path, ffmpeg_path: str | None) -> dict:
    export_dir = export_dir.resolve()
    checks: list[dict] = []

    for name in REQUIRED_EXPORT_FILES:
        path = export_dir / name
        checks.append({
            "name": f"required-file:{name}",
            "ok": path.exists() and path.is_file() and path.stat().st_size > 0,
            "path": str(path),
            "size": path.stat().st_size if path.exists() else 0,
        })

    for name in ["metadata.json", "scenes.json", "prompts.json"]:
        path = export_dir / name
        if path.exists():
            result = check_json(path)
            checks.append({"name": f"json-valid:{name}", "path": str(path), **result})

    for name in ["subtitles.srt", "narration.txt", "caption.txt", "thumbnail_suggestion.txt"]:
        path = export_dir / name
        if path.exists():
            result = check_text_quality(path)
            checks.append({"name": f"text-quality:{name}", "path": str(path), **result})

    ffmpeg = detect_ffmpeg(ffmpeg_path)
    video = export_dir / "final_video.mp4"
    if not ffmpeg:
        checks.append({"name": "ffmpeg-available", "ok": False, "message": "FFmpeg not found."})
    elif video.exists():
        decode = run_ffmpeg_decode(ffmpeg, video)
        checks.append({"name": "ffmpeg-decode", "ok": decode["ok"], "ffmpeg": ffmpeg, **decode})
        metadata = decode.get("metadata", {})
        size = metadata.get("size") or {}
        checks.append({
            "name": "platform-format:vertical-9x16",
            "ok": size.get("height", 0) > size.get("width", 0),
            "size": size,
            "expected": "vertical 9:16 video",
        })
    else:
        checks.append({"name": "ffmpeg-decode", "ok": False, "message": "final_video.mp4 missing."})

    failed = [check for check in checks if not check.get("ok")]
    return {
        "schema": "temple-ai-studio.quality-report.v1",
        "createdAt": now_iso(),
        "exportDir": str(export_dir),
        "overall": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failedChecks": failed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Temple AI Studio local export quality checker.")
    parser.add_argument("--export-dir", required=True, help="Path to a video export package directory.")
    parser.add_argument("--output", help="Optional path for the JSON quality report.")
    parser.add_argument("--ffmpeg", help="Optional explicit ffmpeg.exe path.")
    args = parser.parse_args()

    report = evaluate_export(Path(args.export_dir), args.ffmpeg)
    report_text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report_text, encoding="utf-8")
    print(report_text)
    return 0 if report["overall"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
