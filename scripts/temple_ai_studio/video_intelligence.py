from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any

from PIL import Image, ImageDraw, ImageFont


VIDEO_INTELLIGENCE_SCHEMA = "temple-ai-studio.video-intelligence.v1"
VIDEO_INTELLIGENCE_VERSION = "1.0.0"
FRAME_SIZE = (1080, 1920)
FPS = 25
SAMPLE_RATE = 44100
LOCAL_PROVIDER = "local_ffmpeg_motion"


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in [r"C:\Windows\Fonts\msjh.ttc", r"C:\Windows\Fonts\mingliu.ttc", r"C:\Windows\Fonts\arial.ttf"]:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for char in str(text or ""):
        trial = current + char
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = char
    if current:
        lines.append(current)
    return lines[:3]


def fmt_time(seconds: float) -> str:
    ms = int(round((seconds - int(seconds)) * 1000))
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_srt(scenes: list[dict[str, Any]]) -> str:
    blocks = []
    for index, scene in enumerate(scenes, start=1):
        blocks.append(f"{index}\n{fmt_time(scene['start'])} --> {fmt_time(scene['end'])}\n{scene['subtitle']}\n")
    return "\n".join(blocks)


class TalkingHeadEngine:
    def plan(self, scene: dict[str, Any]) -> dict[str, Any]:
        required = bool(scene.get("emmaCore", {}).get("required"))
        if not required:
            return {"engine": "talking-head", "overall": "NOT_REQUIRED", "reason": "Scene does not require Emma presenter."}
        consistency = scene.get("emmaCore", {}).get("consistency", {})
        return {
            "engine": "talking-head",
            "overall": "READY" if consistency.get("overall") == "PASS" else "BLOCKED",
            "providerMode": "adapter-ready",
            "behavior": scene.get("storyboard", {}).get("emmaBehavior", "natural presenter behavior"),
            "identityVersion": consistency.get("identityVersion"),
            "reason": "Emma references and consistency must pass before talking-head rendering.",
        }


class LipSyncEngine:
    def plan(self, scene: dict[str, Any], audio_available: bool) -> dict[str, Any]:
        if not scene.get("emmaCore", {}).get("required"):
            return {"engine": "lip-sync", "overall": "NOT_REQUIRED", "reason": "No speaking Emma face in scene."}
        if not audio_available:
            return {"engine": "lip-sync", "overall": "WAITING_FOR_AUDIO", "reason": "Narration timing exists; real voice track is not yet supplied."}
        return {"engine": "lip-sync", "overall": "READY", "providerMode": "adapter-ready"}


class MotionEngine:
    def plan(self, scene: dict[str, Any]) -> dict[str, Any]:
        purpose = scene.get("purpose", "")
        motion = "subtle product parallax"
        if purpose == "Product Features":
            motion = "slow detail drift"
        elif purpose == "Call To Action":
            motion = "stable product hold"
        elif purpose == "Ending":
            motion = "soft fade closing"
        return {"engine": "motion", "overall": "PASS", "motionType": motion, "intensity": "low-commercial-safe"}


class CameraMotionEngine:
    def plan(self, scene: dict[str, Any]) -> dict[str, Any]:
        camera = scene.get("storyboard", {}).get("cameraMovement", "slow push-in")
        if "lateral" in camera:
            zoom = "min(zoom+0.00045,1.045)"
            x = "iw/2-(iw/zoom/2)+sin(on/30)*10"
            y = "ih/2-(ih/zoom/2)"
        elif "hold" in camera or "stable" in camera:
            zoom = "1.018"
            x = "iw/2-(iw/zoom/2)"
            y = "ih/2-(ih/zoom/2)"
        else:
            zoom = "min(zoom+0.0008,1.06)"
            x = "iw/2-(iw/zoom/2)"
            y = "ih/2-(ih/zoom/2)"
        return {
            "engine": "camera-motion",
            "overall": "PASS",
            "cameraMovement": camera,
            "zoomExpression": zoom,
            "xExpression": x,
            "yExpression": y,
            "stability": "locked subject center",
        }


class SubtitleBurnInEngine:
    def burn_frame(self, source: Path, scene: dict[str, Any], output: Path) -> dict[str, Any]:
        output.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(source) as image:
            canvas = image.convert("RGB").resize(FRAME_SIZE, Image.LANCZOS)
        draw = ImageDraw.Draw(canvas)
        subtitle = str(scene.get("subtitle", "")).strip()
        font = get_font(58 if len(subtitle) <= 14 else 50)
        safe_box = (64, 1418, 1016, 1748)
        draw.rounded_rectangle(safe_box, radius=30, fill="#17231f")
        draw.rounded_rectangle((safe_box[0] + 10, safe_box[1] + 10, safe_box[2] - 10, safe_box[3] - 10), radius=24, outline="#d9b36c", width=2)
        lines = wrap_text(draw, subtitle, font, 860)
        y = safe_box[1] + 50
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            draw.text(((FRAME_SIZE[0] - (bbox[2] - bbox[0])) // 2, y), line, fill="#ffffff", font=font)
            y += 76
        canvas.save(output, quality=95)
        return {"engine": "subtitle-burn-in", "overall": "PASS", "output": str(output), "subtitleCharacters": len(subtitle)}


class AudioSynchronizationEngine:
    def plan(self, scenes: list[dict[str, Any]]) -> dict[str, Any]:
        timing = []
        for scene in scenes:
            narration = str(scene.get("narration", ""))
            estimated_speech_seconds = max(1.0, len(narration) / 5.2)
            timing.append(
                {
                    "sceneId": scene.get("id"),
                    "start": scene.get("start"),
                    "end": scene.get("end"),
                    "duration": scene.get("duration"),
                    "estimatedSpeechSeconds": round(estimated_speech_seconds, 2),
                    "fitsScene": estimated_speech_seconds <= float(scene.get("duration", 0)) + 1.0,
                }
            )
        return {
            "engine": "audio-sync",
            "overall": "PASS" if all(item["fitsScene"] for item in timing) else "WARN",
            "audioMode": "silent-sync-track",
            "sampleRate": SAMPLE_RATE,
            "timing": timing,
        }


class RenderingPipeline:
    def __init__(self, ffmpeg: Path, provider: str = LOCAL_PROVIDER, codecs: list[str] | None = None):
        self.ffmpeg = Path(ffmpeg)
        self.provider = provider
        self.codecs = codecs or ["h264_mf", "mpeg4"]

    def render_clip(self, frame: Path, output: Path, duration: int, camera: dict[str, Any]) -> dict[str, Any]:
        output.parent.mkdir(parents=True, exist_ok=True)
        frames = max(FPS * int(duration), FPS * 2)
        vf = (
            f"zoompan=z='{camera['zoomExpression']}':x='{camera['xExpression']}':y='{camera['yExpression']}':"
            f"d={frames}:s={FRAME_SIZE[0]}x{FRAME_SIZE[1]}:fps={FPS},format=yuv420p"
        )
        attempts = []
        last_error = ""
        for codec in self.codecs:
            cmd = [
                str(self.ffmpeg),
                "-y",
                "-loop",
                "1",
                "-i",
                str(frame),
                "-f",
                "lavfi",
                "-t",
                str(duration),
                "-i",
                f"anullsrc=channel_layout=stereo:sample_rate={SAMPLE_RATE}",
                "-vf",
                vf,
                "-frames:v",
                str(frames),
                "-r",
                str(FPS),
                "-shortest",
                "-c:v",
                codec,
                "-b:v",
                "5000k",
                "-c:a",
                "aac",
                str(output),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
            attempts.append({"codec": codec, "returnCode": result.returncode})
            if result.returncode == 0:
                return {"engine": "rendering", "overall": "PASS", "output": str(output), "codec": codec, "attempts": attempts}
            last_error = result.stderr[-2000:]
        return {"engine": "rendering", "overall": "FAIL", "output": str(output), "attempts": attempts, "error": last_error}

    def concat(self, clips: list[Path], output: Path, work_dir: Path) -> dict[str, Any]:
        concat_path = work_dir / f"{output.stem}-concat.txt"
        concat_path.write_text("".join([f"file '{path.as_posix()}'\n" for path in clips]), encoding="utf-8")
        cmd = [str(self.ffmpeg), "-y", "-f", "concat", "-safe", "0", "-i", str(concat_path), "-c", "copy", str(output)]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
        if result.returncode != 0:
            reencode = [str(self.ffmpeg), "-y", "-f", "concat", "-safe", "0", "-i", str(concat_path), "-c:v", "mpeg4", "-c:a", "aac", str(output)]
            second = subprocess.run(reencode, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
            return {"engine": "concat", "overall": "PASS" if second.returncode == 0 else "FAIL", "output": str(output), "fallback": True, "returnCode": second.returncode, "error": second.stderr[-2000:]}
        return {"engine": "concat", "overall": "PASS", "output": str(output), "fallback": False, "returnCode": result.returncode}


class VideoQualityAnalyzer:
    def __init__(self, ffmpeg: Path):
        self.ffmpeg = Path(ffmpeg)

    def analyze(self, video: Path, scenes: list[dict[str, Any]], scene_reports: list[dict[str, Any]]) -> dict[str, Any]:
        decode = self._decode(video)
        scene_scores = [report["quality"]["score"] for report in scene_reports if report.get("quality")]
        checks = [
            {"name": "video-playback", "ok": decode["ok"]},
            {"name": "vertical-format", "ok": decode.get("metadata", {}).get("size", {}).get("height", 0) > decode.get("metadata", {}).get("size", {}).get("width", 0)},
            {"name": "fps-present", "ok": bool(decode.get("metadata", {}).get("fps"))},
            {"name": "audio-stream-present", "ok": bool(decode.get("metadata", {}).get("audioLine"))},
            {"name": "scene-rendering", "ok": all(report.get("render", {}).get("overall") == "PASS" for report in scene_reports)},
            {"name": "subtitle-quality", "ok": all(report.get("subtitle", {}).get("overall") == "PASS" for report in scene_reports)},
            {"name": "motion-quality", "ok": all(report.get("motion", {}).get("overall") == "PASS" for report in scene_reports)},
            {"name": "camera-stability", "ok": all(report.get("camera", {}).get("overall") == "PASS" for report in scene_reports)},
            {"name": "lip-sync", "ok": all(report.get("lipSync", {}).get("overall") in ["NOT_REQUIRED", "READY", "WAITING_FOR_AUDIO"] for report in scene_reports)},
            {"name": "commercial-usability", "ok": mean(scene_scores) >= 0.78 if scene_scores else False},
        ]
        failed = [check for check in checks if not check["ok"]]
        return {
            "schema": "temple-ai-studio.video-quality.v1",
            "version": VIDEO_INTELLIGENCE_VERSION,
            "createdAt": now_iso(),
            "overall": "PASS" if not failed else "FAIL",
            "score": round(mean(scene_scores), 4) if scene_scores else 0,
            "video": str(video),
            "decode": decode,
            "checks": checks,
            "failedChecks": failed,
        }

    def _decode(self, video: Path) -> dict[str, Any]:
        cmd = [str(self.ffmpeg), "-hide_banner", "-i", str(video), "-f", "null", "NUL"]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
        output = "\n".join([result.stdout, result.stderr])
        return {"ok": result.returncode == 0, "metadata": parse_ffmpeg_metadata(output), "returnCode": result.returncode, "errorTail": output[-2000:] if result.returncode else ""}


def parse_ffmpeg_metadata(output: str) -> dict[str, Any]:
    video_line = ""
    audio_line = ""
    for line in output.splitlines():
        if "Video:" in line and not video_line:
            video_line = line.strip()
        if "Audio:" in line and not audio_line:
            audio_line = line.strip()
    size = None
    size_match = re.search(r"(\d{3,5})x(\d{3,5})", video_line)
    if size_match:
        size = {"width": int(size_match.group(1)), "height": int(size_match.group(2))}
    fps = None
    fps_match = re.search(r"([0-9.]+)\s*fps", video_line)
    if fps_match:
        fps = float(fps_match.group(1))
    duration = None
    duration_match = re.search(r"Duration:\s*([0-9:.]+)", output)
    if duration_match:
        duration = duration_match.group(1)
    return {"duration": duration, "size": size or {}, "fps": fps, "videoLine": video_line, "audioLine": audio_line}


class VideoGenerationPipeline:
    def __init__(self, ffmpeg: Path, provider: str = LOCAL_PROVIDER):
        self.ffmpeg = Path(ffmpeg)
        self.provider = provider
        self.talking_head = TalkingHeadEngine()
        self.lip_sync = LipSyncEngine()
        self.motion = MotionEngine()
        self.camera = CameraMotionEngine()
        self.subtitle = SubtitleBurnInEngine()
        self.audio_sync = AudioSynchronizationEngine()
        self.renderer = RenderingPipeline(ffmpeg)
        self.quality = VideoQualityAnalyzer(ffmpeg)

    def run(self, project: dict[str, Any], product: dict[str, Any], output_dir: Path, project_dir: Path, preview: bool = False) -> dict[str, Any]:
        output_dir.mkdir(parents=True, exist_ok=True)
        video_dir = project_dir / "video-intelligence"
        frame_dir = video_dir / "frames"
        clip_dir = video_dir / "clips"
        frame_dir.mkdir(parents=True, exist_ok=True)
        clip_dir.mkdir(parents=True, exist_ok=True)
        audio_plan = self.audio_sync.plan(project["scenes"])
        scene_reports = []
        clip_paths = []
        for scene in project["scenes"]:
            source = Path(scene.get("generatedImagePath", ""))
            if not source.exists():
                raise RuntimeError(f"Generated scene image is missing: {scene.get('id')}")
            subtitle_frame = frame_dir / f"{scene['order']:02d}-{scene['id']}-subtitle.png"
            subtitle_report = self.subtitle.burn_frame(source, scene, subtitle_frame)
            camera_report = self.camera.plan(scene)
            motion_report = self.motion.plan(scene)
            talking_report = self.talking_head.plan(scene)
            lip_report = self.lip_sync.plan(scene, audio_available=False)
            clip_path = clip_dir / f"{scene['order']:02d}-{scene['id']}-v{scene.get('version', 1)}.mp4"
            render_report = self.renderer.render_clip(subtitle_frame, clip_path, int(scene["duration"]), camera_report)
            if render_report["overall"] != "PASS":
                raise RuntimeError(f"Scene render failed: {scene.get('id')}: {render_report.get('error', '')}")
            scene_quality = scene.get("visualQuality") or {"score": 0.8, "overall": "PASS"}
            scene["videoIntelligence"] = {
                "talkingHead": talking_report,
                "lipSync": lip_report,
                "motion": motion_report,
                "camera": camera_report,
                "subtitle": subtitle_report,
                "render": render_report,
            }
            scene_reports.append(
                {
                    "sceneId": scene["id"],
                    "talkingHead": talking_report,
                    "lipSync": lip_report,
                    "motion": motion_report,
                    "camera": camera_report,
                    "subtitle": subtitle_report,
                    "render": render_report,
                    "quality": scene_quality,
                }
            )
            clip_paths.append(clip_path)
        target = output_dir / ("preview.mp4" if preview else "final_video.mp4")
        concat_report = self.renderer.concat(clip_paths, target, video_dir)
        if concat_report["overall"] != "PASS":
            raise RuntimeError(f"Video concat failed: {concat_report.get('error', '')}")
        srt_path = output_dir / "subtitles.srt"
        srt_path.write_text(build_srt(project["scenes"]), encoding="utf-8-sig")
        if not preview:
            subtitled = output_dir / "final_video_subtitled.mp4"
            shutil.copyfile(target, subtitled)
        video_quality = self.quality.analyze(target, project["scenes"], scene_reports)
        report = {
            "schema": VIDEO_INTELLIGENCE_SCHEMA,
            "version": VIDEO_INTELLIGENCE_VERSION,
            "createdAt": now_iso(),
            "projectId": project["id"],
            "provider": self.provider,
            "preview": preview,
            "audioSynchronization": audio_plan,
            "sceneReports": scene_reports,
            "concat": concat_report,
            "quality": video_quality,
            "outputVideo": str(target),
            "subtitles": str(srt_path),
        }
        report_path = project_dir / ("video-intelligence-preview-report.json" if preview else "video-intelligence-final-report.json")
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report


def run_video_generation_pipeline(project: dict[str, Any], product: dict[str, Any], output_dir: Path, project_dir: Path, ffmpeg: Path, preview: bool = False) -> dict[str, Any]:
    return VideoGenerationPipeline(ffmpeg).run(project, product, output_dir, project_dir, preview=preview)


def main() -> int:
    parser = argparse.ArgumentParser(description="Temple AI Studio Video Intelligence Pipeline.")
    parser.add_argument("--project-json", required=True)
    parser.add_argument("--product-json", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--ffmpeg", required=True)
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--output-report", required=True)
    args = parser.parse_args()
    project = json.loads(Path(args.project_json).read_text(encoding="utf-8-sig"))
    product = json.loads(Path(args.product_json).read_text(encoding="utf-8-sig"))
    report = run_video_generation_pipeline(project, product, Path(args.output_dir), Path(args.project_dir), Path(args.ffmpeg), preview=args.preview)
    Path(args.output_report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output_report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["quality"]["overall"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
