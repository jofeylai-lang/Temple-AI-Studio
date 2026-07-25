from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from .real_providers import (
    ComfyUIProductionClient,
    ProviderExecutionError,
    Qwen3TTSProductionClient,
)


VIDEO_INTELLIGENCE_SCHEMA = "temple-ai-studio.video-intelligence.v1"
VIDEO_INTELLIGENCE_VERSION = "1.0.1"
FRAME_SIZE = (1080, 1920)
FPS = 25
SAMPLE_RATE = 44100
LOCAL_PROVIDER = "local_hybrid_video_pipeline"


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
        direct_speech = scene.get("speechMode") == "direct-to-camera"
        if not required or not direct_speech:
            return {
                "engine": "talking-head",
                "overall": "NOT_REQUIRED",
                "providerMode": "voice-over-b-roll",
                "reason": "This scene uses approved Emma B-roll with narration voice-over, not direct-to-camera speech.",
            }
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
        direct_speech = scene.get("speechMode") == "direct-to-camera"
        if not scene.get("emmaCore", {}).get("required") or not direct_speech:
            return {
                "engine": "lip-sync",
                "overall": "NOT_REQUIRED",
                "providerMode": "voice-over-b-roll",
                "reason": "MuseTalk is not used because the scene is edited as narration over B-roll rather than direct speech.",
            }
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
        paths = {
            "Hook": "locked-establishing",
            "Introduction": "slow-upward-reveal",
            "Product Features": "slow-detail-rise",
            "Spiritual Value": "slow-right-drift",
            "Call To Action": "slow-left-drift",
            "Ending": "locked-closing",
        }
        path = paths.get(scene.get("purpose", ""), "locked-hold")
        return {
            "engine": "camera-motion",
            "overall": "PASS",
            "cameraMovement": camera,
            "motionPath": path,
            "motionSignature": path,
            "zoomExpression": "1.0",
            "xExpression": "deterministic",
            "yExpression": "deterministic",
            "usesFrameRandomness": False,
            "stability": "deterministic fixed path; no sine or random frame offsets",
        }


class SubtitleBurnInEngine:
    def burn_frame(self, source: Path, scene: dict[str, Any], output: Path) -> dict[str, Any]:
        output.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(source) as image:
            canvas = image.convert("RGB").resize(FRAME_SIZE, Image.LANCZOS)
        draw = ImageDraw.Draw(canvas)
        subtitle = str(scene.get("subtitle", "")).strip()
        font = get_font(58 if len(subtitle) <= 14 else 50)
        lines = wrap_text(draw, subtitle, font, 860)
        box_height = 82 + max(1, len(lines)) * 76
        safe_box = (64, 1748 - box_height, 1016, 1748)
        draw.rounded_rectangle(safe_box, radius=30, fill="#17231f")
        draw.rounded_rectangle((safe_box[0] + 10, safe_box[1] + 10, safe_box[2] - 10, safe_box[3] - 10), radius=24, outline="#d9b36c", width=2)
        y = safe_box[1] + 38
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            draw.text(((FRAME_SIZE[0] - (bbox[2] - bbox[0])) // 2, y), line, fill="#ffffff", font=font)
            y += 76
        canvas.save(output, quality=95)
        return {"engine": "subtitle-burn-in", "overall": "PASS", "output": str(output), "subtitleCharacters": len(subtitle)}

    def create_overlay(self, scene: dict[str, Any], output: Path) -> dict[str, Any]:
        output.parent.mkdir(parents=True, exist_ok=True)
        canvas = Image.new("RGBA", FRAME_SIZE, (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        subtitle = str(scene.get("subtitle", "")).strip()
        font = get_font(58 if len(subtitle) <= 14 else 50)
        lines = wrap_text(draw, subtitle, font, 860)
        box_height = 82 + max(1, len(lines)) * 76
        safe_box = (64, 1748 - box_height, 1016, 1748)
        draw.rounded_rectangle(safe_box, radius=30, fill=(23, 35, 31, 232))
        draw.rounded_rectangle(
            (safe_box[0] + 10, safe_box[1] + 10, safe_box[2] - 10, safe_box[3] - 10),
            radius=24,
            outline=(217, 179, 108, 255),
            width=2,
        )
        y = safe_box[1] + 38
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            draw.text(((FRAME_SIZE[0] - (bbox[2] - bbox[0])) // 2, y), line, fill="#ffffff", font=font)
            y += 76
        canvas.save(output)
        return {
            "engine": "subtitle-overlay",
            "overall": "PASS",
            "output": str(output),
            "subtitleCharacters": len(subtitle),
        }


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


class NarrationEngine:
    def __init__(self, production_root: Path):
        self.production_root = Path(production_root)

    def synthesize(self, scenes: list[dict[str, Any]], project_dir: Path) -> dict[str, Any]:
        registry = json.loads(
            (self.production_root / "providers" / "providers.json").read_text(
                encoding="utf-8-sig"
            )
        )
        provider = next(
            (
                item
                for item in registry.get("providers", [])
                if item.get("id") == "qwen3-tts-local"
                and item.get("enabled") is True
                and item.get("paid") is False
            ),
            None,
        )
        if not provider:
            raise RuntimeError("The approved local Qwen3-TTS provider is unavailable.")
        identity = json.loads(
            (self.production_root / "avatar" / "identity" / "emma.core.json").read_text(
                encoding="utf-8-sig"
            )
        )
        profile_path = Path(
            identity.get("productionActivation", {}).get("voiceProfile")
            or identity.get("activation", {}).get("voiceProfile", "")
        )
        if not profile_path.is_file():
            raise RuntimeError("The canonical Emma voice profile is unavailable.")
        profile = json.loads(profile_path.read_text(encoding="utf-8-sig"))
        if profile.get("profileId") != "emma-canonical-video-voice-v1":
            raise RuntimeError(
                f"Unexpected Emma voice profile: {profile.get('profileId')}"
            )
        narration = "。".join(
            str(scene.get("narration", "")).strip().rstrip("。")
            for scene in scenes
            if str(scene.get("narration", "")).strip()
        ) + "。"
        output = Path(project_dir) / "video-intelligence" / "audio" / "emma-narration.wav"
        client = Qwen3TTSProductionClient(
            Path(provider["python"]),
            Path(__file__).resolve().parents[1] / "qwen3_tts_worker.py",
            Path(provider["modelPath"]),
        )
        result = client.synthesize(
            narration,
            Path(profile["referenceAudio"]),
            str(profile["referenceText"]),
            output,
        )
        return {
            **result,
            "voiceProfileId": profile["profileId"],
            "voiceProfile": str(profile_path),
            "referenceAudio": profile["referenceAudio"],
            "referenceSourceVideo": profile.get("referenceSourceVideo"),
            "referenceSourceTimestamp": profile.get("referenceSourceTimestamp"),
            "narration": narration,
        }


class RealSceneVideoGenerator:
    def __init__(self, production_root: Path):
        self.production_root = Path(production_root)

    def prepare(self, project: dict[str, Any], project_dir: Path) -> list[dict[str, Any]]:
        targets = [
            scene
            for scene in project.get("scenes", [])
            if scene.get("preferLocalVideoGeneration")
            and not Path(scene.get("generatedVideoPath", "")).is_file()
        ]
        if not targets:
            return []
        registry_path = self.production_root / "providers" / "providers.json"
        if not registry_path.is_file():
            return []
        registry = json.loads(registry_path.read_text(encoding="utf-8-sig"))
        provider = next(
            (
                item
                for item in registry.get("providers", [])
                if item.get("id") == "wan22-ti2v-local"
                and item.get("enabled") is True
                and item.get("paid") is False
            ),
            None,
        )
        if not provider:
            return []
        client = ComfyUIProductionClient(provider.get("endpoint", "http://127.0.0.1:8188"))
        client.health()
        results = []
        for scene in targets[:1]:
            root_source = Path(scene.get("visualProvenance", {}).get("sourceImage", ""))
            if not root_source.is_file():
                raise ProviderExecutionError(
                    f"Wan 2.2 scene source is unavailable: {scene.get('id')}"
                )
            uploaded = client.upload_image(
                root_source,
                subfolder=f"temple-ai-studio/{project.get('id', 'project')}",
            )
            generation = provider.get("generation", {})
            prompt = scene.get("providerPrompts", {}).get("wan", {})
            output_dir = Path(project_dir) / "vgen" / f"s{scene.get('order', 0)}"
            result = client.run_descriptor(
                Path(provider["workflowDescriptor"]),
                {
                    "prompt": prompt.get("positive", ""),
                    "negative_prompt": prompt.get("negative", ""),
                    "seed": abs(hash((project.get("id"), scene.get("id"), scene.get("version", 1)))) % 2_147_483_647,
                    "width": int(generation.get("width", 480)),
                    "height": int(generation.get("height", 832)),
                    "num_frames": min(49, int(generation.get("maxFrames", 49))),
                    "fps": int(generation.get("fps", 16)),
                    "first_frame": uploaded["comfyPath"],
                    "output_prefix": f"tas-s{scene.get('order', 0)}-wan22",
                },
                output_dir,
                timeout=2100,
            )
            artifact = next(
                (
                    Path(item["path"])
                    for item in result.get("artifacts", [])
                    if item.get("mediaType") in {"video", "videos", "gifs"}
                    and Path(item["path"]).is_file()
                ),
                None,
            )
            if not artifact:
                raise ProviderExecutionError(
                    f"Wan 2.2 returned no playable scene artifact: {scene.get('id')}"
                )
            scene["generatedVideoPath"] = str(artifact)
            scene["videoProvenance"] = {
                "provider": provider["id"],
                "workflow": provider["workflowDescriptor"],
                "promptId": result.get("promptId"),
                "sourceImage": str(root_source),
                "artifact": str(artifact),
                "provenance": "real-production",
            }
            results.append(scene["videoProvenance"])
        return results


class RenderingPipeline:
    def __init__(self, ffmpeg: Path, provider: str = LOCAL_PROVIDER, codecs: list[str] | None = None):
        self.ffmpeg = Path(ffmpeg)
        self.provider = provider
        self.codecs = codecs or ["libx264", "h264_mf", "mpeg4"]

    def render_clip(self, frame: Path, output: Path, duration: float, camera: dict[str, Any]) -> dict[str, Any]:
        output.parent.mkdir(parents=True, exist_ok=True)
        frames = max(1, round(FPS * float(duration)))
        vf = self._still_filter(camera, frames)
        attempts = []
        last_error = ""
        for codec in self.codecs:
            video_args = self._video_args(codec)
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
                *video_args,
                "-c:a",
                "aac",
                "-b:a",
                "96k",
                "-movflags",
                "+faststart",
                str(output),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
            attempts.append({"codec": codec, "returnCode": result.returncode, "videoArgs": video_args})
            if result.returncode == 0:
                return {
                    "engine": "rendering",
                    "overall": "PASS",
                    "output": str(output),
                    "codec": codec,
                    "videoArgs": video_args,
                    "attempts": attempts,
                    "renderMode": "stabilized-still",
                    "motionSignature": camera["motionSignature"],
                    "source": str(frame),
                }
            last_error = result.stderr[-2000:]
        return {"engine": "rendering", "overall": "FAIL", "output": str(output), "attempts": attempts, "error": last_error}

    def render_video_clip(
        self,
        source: Path,
        overlay: Path,
        output: Path,
        duration: float,
        source_role: str,
        start_seconds: float = 0.0,
    ) -> dict[str, Any]:
        output.parent.mkdir(parents=True, exist_ok=True)
        attempts = []
        last_error = ""
        for codec in self.codecs:
            video_args = self._video_args(codec)
            filter_graph = (
                f"[0:v]scale={FRAME_SIZE[0]}:{FRAME_SIZE[1]}:"
                "force_original_aspect_ratio=increase,"
                f"crop={FRAME_SIZE[0]}:{FRAME_SIZE[1]},setsar=1,fps={FPS},"
                f"tpad=stop_mode=clone:stop_duration={float(duration):.3f}[base];"
                "[1:v]format=rgba[overlay];"
                "[base][overlay]overlay=0:0:shortest=1,format=yuv420p[outv]"
            )
            cmd = [
                str(self.ffmpeg),
                "-y",
                "-ss",
                str(max(0.0, float(start_seconds))),
                "-i",
                str(source),
                "-loop",
                "1",
                "-i",
                str(overlay),
                "-f",
                "lavfi",
                "-t",
                str(duration),
                "-i",
                f"anullsrc=channel_layout=stereo:sample_rate={SAMPLE_RATE}",
                "-filter_complex",
                filter_graph,
                "-map",
                "[outv]",
                "-map",
                "2:a",
                "-t",
                str(duration),
                "-r",
                str(FPS),
                *video_args,
                "-c:a",
                "aac",
                "-b:a",
                "96k",
                "-movflags",
                "+faststart",
                str(output),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240)
            attempts.append({"codec": codec, "returnCode": result.returncode, "videoArgs": video_args})
            if result.returncode == 0:
                return {
                    "engine": "rendering",
                    "overall": "PASS",
                    "output": str(output),
                    "codec": codec,
                    "videoArgs": video_args,
                    "attempts": attempts,
                    "renderMode": source_role,
                    "motionSignature": f"{source_role}:native-motion:{source.stem}",
                    "source": str(source),
                    "sourceStartSeconds": float(start_seconds),
                }
            last_error = result.stderr[-2000:]
        return {
            "engine": "rendering",
            "overall": "FAIL",
            "output": str(output),
            "attempts": attempts,
            "error": last_error,
        }

    @staticmethod
    def _still_filter(camera: dict[str, Any], frames: int) -> str:
        max_frame = max(1, frames - 1)
        path = camera.get("motionPath", "locked-hold")
        x = "60"
        y = "107"
        if path == "slow-upward-reveal":
            y = f"180-(146*n/{max_frame})"
        elif path == "slow-detail-rise":
            y = f"126-(38*n/{max_frame})"
        elif path == "slow-right-drift":
            x = f"12+(96*n/{max_frame})"
        elif path == "slow-left-drift":
            x = f"108-(96*n/{max_frame})"
        return (
            "scale=1200:2134:flags=lanczos,"
            f"crop={FRAME_SIZE[0]}:{FRAME_SIZE[1]}:x='{x}':y='{y}',"
            f"fps={FPS},format=yuv420p"
        )

    def _video_args(self, codec: str) -> list[str]:
        if codec == "libx264":
            return ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-profile:v", "high", "-pix_fmt", "yuv420p"]
        if codec == "h264_mf":
            return ["-c:v", "h264_mf", "-b:v", "8000k", "-pix_fmt", "yuv420p"]
        return ["-c:v", codec, "-b:v", "6500k", "-pix_fmt", "yuv420p"]

    def concat(self, clips: list[Path], output: Path, work_dir: Path) -> dict[str, Any]:
        concat_path = work_dir / f"{output.stem}-concat.txt"
        concat_path.write_text("".join([f"file '{path.as_posix()}'\n" for path in clips]), encoding="utf-8")
        cmd = [str(self.ffmpeg), "-y", "-f", "concat", "-safe", "0", "-i", str(concat_path), "-c", "copy", str(output)]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
        if result.returncode != 0:
            reencode = [str(self.ffmpeg), "-y", "-f", "concat", "-safe", "0", "-i", str(concat_path), "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-c:a", "aac", "-movflags", "+faststart", str(output)]
            second = subprocess.run(reencode, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
            return {"engine": "concat", "overall": "PASS" if second.returncode == 0 else "FAIL", "output": str(output), "fallback": True, "returnCode": second.returncode, "error": second.stderr[-2000:]}
        return {"engine": "concat", "overall": "PASS", "output": str(output), "fallback": False, "returnCode": result.returncode}

    def mux_narration(
        self,
        video: Path,
        narration: Path,
        output: Path,
        duration: float,
    ) -> dict[str, Any]:
        temporary = output.with_name(f"{output.stem}-with-narration.tmp.mp4")
        probe = subprocess.run(
            [
                str(self.ffmpeg),
                "-hide_banner",
                "-i",
                str(narration),
                "-f",
                "null",
                "NUL",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )
        narration_metadata = parse_ffmpeg_metadata(
            "\n".join([probe.stdout, probe.stderr])
        )
        source_duration = timecode_seconds(narration_metadata.get("duration"))
        target_duration = max(0.1, float(duration))
        playback_rate = (
            max(1.0, min(2.0, float(source_duration) / target_duration))
            if source_duration
            else 1.0
        )
        command = [
            str(self.ffmpeg),
            "-y",
            "-i",
            str(video),
            "-i",
            str(narration),
            "-filter_complex",
            (
                f"[1:a]atempo={playback_rate:.6f},"
                f"apad,atrim=0:{target_duration:.3f}[voice]"
            ),
            "-map",
            "0:v:0",
            "-map",
            "[voice]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-t",
            str(duration),
            "-movflags",
            "+faststart",
            str(temporary),
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
        if result.returncode != 0 or not temporary.is_file():
            return {
                "engine": "narration-mux",
                "overall": "FAIL",
                "error": result.stderr[-2000:],
            }
        temporary.replace(output)
        return {
            "engine": "narration-mux",
            "overall": "PASS",
            "output": str(output),
            "narration": str(narration),
            "duration": float(duration),
            "sourceDuration": source_duration,
            "playbackRate": round(playback_rate, 6),
            "durationFitted": bool(
                source_duration
                and (source_duration / playback_rate) <= target_duration + 0.05
            ),
        }


class VideoQualityAnalyzer:
    def __init__(self, ffmpeg: Path):
        self.ffmpeg = Path(ffmpeg)

    def analyze(
        self,
        video: Path,
        scenes: list[dict[str, Any]],
        scene_reports: list[dict[str, Any]],
        narration_mux: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        decode = self._decode(video)
        scene_scores = [report["quality"]["score"] for report in scene_reports if report.get("quality")]
        expected_duration = round(sum(float(scene.get("duration", 0)) for scene in scenes), 3)
        actual_duration = timecode_seconds(decode.get("metadata", {}).get("duration"))
        provenance = [
            report.get("provenance", {})
            for report in scene_reports
            if report.get("render", {}).get("overall") == "PASS"
        ]
        roots = [str(item.get("rootSource", "")).lower() for item in provenance if item.get("rootSource")]
        root_counts = Counter(roots)
        meaningful_scenes = len(provenance)
        unique_root_sources = len(root_counts)
        max_root_share = max(root_counts.values(), default=0) / max(1, meaningful_scenes)
        render_modes = [report.get("render", {}).get("renderMode", "") for report in scene_reports]
        video_scene_count = sum(mode in {"approved-source-video", "wan22-generated-video", "generated-video"} for mode in render_modes)
        motion_signatures = [
            str(report.get("render", {}).get("motionSignature", ""))
            for report in scene_reports
            if report.get("render", {}).get("motionSignature")
        ]
        unique_motion_signatures = len(set(motion_signatures))
        repeated_motion_ratio = 1.0 - (unique_motion_signatures / max(1, len(motion_signatures)))
        long_form = expected_duration >= 20
        minimum_scenes = 5 if long_form else min(3, len(scenes))
        minimum_unique_sources = 5 if long_form else min(3, len(scenes))
        max_allowed_share = 0.40 if long_form else 0.50
        deterministic_camera = all(
            not report.get("camera", {}).get("usesFrameRandomness", True)
            and "sin(" not in str(report.get("camera", {}).get("xExpression", ""))
            for report in scene_reports
        )
        emma_required = any(
            bool(scene.get("emmaCore", {}).get("required"))
            for scene in scenes
        )
        narration_ready = bool(
            narration_mux
            and narration_mux.get("overall") == "PASS"
            and narration_mux.get("durationFitted")
        )
        required_video_scenes = 2 if long_form else 1
        expected_progression = [
            "Hook",
            "Introduction",
            "Product Features",
            "Spiritual Value",
            "Call To Action",
            "Ending",
        ]
        actual_progression = [str(scene.get("purpose", "")) for scene in scenes]
        progression_ok = actual_progression == expected_progression[: len(actual_progression)]
        scene_alignment_ready = all(
            bool(scene.get("storyboard", {}).get("sourcePrompt"))
            and bool(scene.get("narration"))
            and bool(scene.get("subtitle"))
            and bool(report.get("provenance", {}).get("rootSource"))
            for scene, report in zip(scenes, scene_reports)
        )
        checks = [
            {"name": "video-playback", "ok": decode["ok"]},
            {"name": "vertical-format", "ok": decode.get("metadata", {}).get("size", {}).get("height", 0) > decode.get("metadata", {}).get("size", {}).get("width", 0)},
            {"name": "fps-present", "ok": bool(decode.get("metadata", {}).get("fps"))},
            {"name": "audio-stream-present", "ok": bool(decode.get("metadata", {}).get("audioLine"))},
            {
                "name": "real-narration-audio",
                "ok": not emma_required or narration_ready,
                "emmaRequired": emma_required,
            },
            {
                "name": "narration-duration-fit",
                "ok": not emma_required or narration_ready,
                "sourceSeconds": (
                    narration_mux.get("sourceDuration") if narration_mux else None
                ),
                "playbackRate": (
                    narration_mux.get("playbackRate") if narration_mux else None
                ),
                "targetSeconds": expected_duration,
            },
            {
                "name": "duration-target",
                "ok": actual_duration is not None
                and abs(actual_duration - expected_duration) <= 0.25,
                "expectedSeconds": expected_duration,
                "actualSeconds": actual_duration,
            },
            {"name": "scene-rendering", "ok": all(report.get("render", {}).get("overall") == "PASS" for report in scene_reports)},
            {
                "name": "meaningful-scene-count",
                "ok": meaningful_scenes >= minimum_scenes,
                "actual": meaningful_scenes,
                "minimum": minimum_scenes,
            },
            {
                "name": "unique-root-assets",
                "ok": unique_root_sources >= minimum_unique_sources,
                "actual": unique_root_sources,
                "minimum": minimum_unique_sources,
            },
            {
                "name": "no-dominant-asset",
                "ok": max_root_share <= max_allowed_share,
                "actual": round(max_root_share, 4),
                "maximum": max_allowed_share,
            },
            {
                "name": "real-motion-present",
                "ok": video_scene_count >= required_video_scenes,
                "videoScenes": video_scene_count,
                "minimum": required_video_scenes,
            },
            {
                "name": "camera-jitter-metadata",
                "ok": deterministic_camera,
                "reason": "Camera paths must not use random or sinusoidal per-frame offsets.",
            },
            {
                "name": "non-repeating-camera-language",
                "ok": unique_motion_signatures >= min(3, len(scene_reports))
                and repeated_motion_ratio <= 0.50,
                "uniqueSignatures": unique_motion_signatures,
                "repeatedRatio": round(repeated_motion_ratio, 4),
            },
            {
                "name": "meaningful-shot-progression",
                "ok": progression_ok,
                "actual": actual_progression,
                "expected": expected_progression[: len(actual_progression)],
            },
            {
                "name": "scene-to-script-alignment-metadata",
                "ok": scene_alignment_ready,
                "reason": "Every rendered scene must retain its storyboard prompt, narration, subtitle, and source provenance.",
            },
            {"name": "subtitle-quality", "ok": all(report.get("subtitle", {}).get("overall") == "PASS" for report in scene_reports)},
            {"name": "motion-quality", "ok": all(report.get("motion", {}).get("overall") == "PASS" for report in scene_reports)},
            {"name": "camera-stability", "ok": deterministic_camera and all(report.get("camera", {}).get("overall") == "PASS" for report in scene_reports)},
            {"name": "lip-sync", "ok": all(report.get("lipSync", {}).get("overall") in ["NOT_REQUIRED", "READY", "WAITING_FOR_AUDIO"] for report in scene_reports)},
        ]
        editorial_components = [
            1.0 if decode["ok"] else 0.0,
            min(1.0, meaningful_scenes / max(1, minimum_scenes)),
            min(1.0, unique_root_sources / max(1, minimum_unique_sources)),
            max(0.0, 1.0 - max_root_share),
            min(1.0, unique_motion_signatures / max(1, min(3, len(scene_reports)))),
            min(1.0, video_scene_count / 2),
            mean(scene_scores) if scene_scores else 0.0,
        ]
        editorial_score = round(mean(editorial_components), 4)
        checks.append({"name": "commercial-usability", "ok": editorial_score >= 0.78, "score": editorial_score})
        failed = [check for check in checks if not check["ok"]]
        return {
            "schema": "temple-ai-studio.video-quality.v1",
            "version": VIDEO_INTELLIGENCE_VERSION,
            "createdAt": now_iso(),
            "overall": "PASS" if not failed else "FAIL",
            "score": editorial_score,
            "video": str(video),
            "decode": decode,
            "editorialMetrics": {
                "meaningfulSceneCount": meaningful_scenes,
                "uniqueRootSourceCount": unique_root_sources,
                "rootSourceCounts": dict(root_counts),
                "maxRootSourceShare": round(max_root_share, 4),
                "videoSceneCount": video_scene_count,
                "stillSceneCount": len(render_modes) - video_scene_count,
                "uniqueMotionSignatureCount": unique_motion_signatures,
                "repeatedMotionRatio": round(repeated_motion_ratio, 4),
            },
            "checks": checks,
            "failedChecks": failed,
        }

    def _decode(self, video: Path) -> dict[str, Any]:
        cmd = [str(self.ffmpeg), "-hide_banner", "-i", str(video), "-f", "null", "NUL"]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
        output = "\n".join([result.stdout, result.stderr])
        return {"ok": result.returncode == 0, "metadata": parse_ffmpeg_metadata(output), "returnCode": result.returncode, "errorTail": output[-2000:] if result.returncode else ""}

    def analyze_frames(
        self,
        video: Path,
        production_root: Path,
        expected_scenes: int,
        output: Path,
    ) -> dict[str, Any]:
        registry_path = Path(production_root) / "providers" / "providers.json"
        if not registry_path.is_file():
            raise RuntimeError("Production provider registry is unavailable for frame analysis.")
        registry = json.loads(registry_path.read_text(encoding="utf-8-sig"))
        provider = next(
            (
                item
                for item in registry.get("providers", [])
                if "quality-video" in item.get("capabilities", [])
                and item.get("enabled") is True
            ),
            None,
        )
        if not provider:
            raise RuntimeError("No enabled local video quality provider is available.")
        openclip_path = Path(provider.get("modelRoot", production_root)) / next(
            (
                item
                for item in provider.get("requiredModels", [])
                if "openclip" in item.lower()
            ),
            "",
        )
        worker = Path(__file__).resolve().parents[1] / "video_quality_worker.py"
        command = [
            str(Path(provider["runtimePath"])),
            str(worker),
            "--video",
            str(video),
            "--ffmpeg",
            str(self.ffmpeg),
            "--expected-scenes",
            str(expected_scenes),
            "--openclip",
            str(openclip_path),
            "--editorial-only",
            "--output",
            str(output),
        ]
        cache_root = Path(production_root) / "cache" / "huggingface"
        cache_root.mkdir(parents=True, exist_ok=True)
        worker_environment = dict(os.environ)
        worker_environment["HF_HOME"] = str(cache_root)
        worker_environment["XDG_CACHE_HOME"] = str(cache_root)
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
            env=worker_environment,
        )
        if result.returncode != 0 or not output.is_file():
            raise RuntimeError(f"Frame-level editorial analysis failed: {result.stderr[-2000:]}")
        return json.loads(output.read_text(encoding="utf-8-sig"))

    @staticmethod
    def merge_frame_analysis(quality: dict[str, Any], frame_report: dict[str, Any]) -> dict[str, Any]:
        frame_checks = [
            {"name": f"frame-{name}", "ok": bool(ok)}
            for name, ok in frame_report.get("checks", {}).items()
        ]
        quality["checks"].extend(frame_checks)
        quality["failedChecks"].extend(check for check in frame_checks if not check["ok"])
        quality["editorialMetrics"]["frameAnalysis"] = {
            "motion": frame_report.get("motion", {}),
            "editorial": frame_report.get("editorial", {}),
        }
        frame_score = mean([1.0 if check["ok"] else 0.0 for check in frame_checks]) if frame_checks else 0.0
        quality["score"] = round(min(float(quality.get("score", 0.0)), frame_score), 4)
        quality["overall"] = "PASS" if not quality["failedChecks"] else "FAIL"
        return quality


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


def timecode_seconds(value: str | None) -> float | None:
    if not value:
        return None
    parts = value.split(":")
    if len(parts) != 3:
        return None
    try:
        return round(
            int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2]),
            3,
        )
    except ValueError:
        return None


class VideoGenerationPipeline:
    def __init__(self, ffmpeg: Path, provider: str = LOCAL_PROVIDER, production_root: Path | None = None):
        self.ffmpeg = Path(ffmpeg)
        self.provider = provider
        self.production_root = Path(production_root) if production_root else None
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
        generated_video_evidence = [
            scene["videoProvenance"]
            for scene in project.get("scenes", [])
            if scene.get("videoProvenance")
        ]
        if self.production_root:
            generated_video_evidence.extend(
                RealSceneVideoGenerator(self.production_root).prepare(project, project_dir)
            )
        narration_report = (
            NarrationEngine(self.production_root).synthesize(project["scenes"], project_dir)
            if self.production_root
            else None
        )
        audio_plan = self.audio_sync.plan(project["scenes"])
        if narration_report:
            audio_plan["audioMode"] = "emma-canonical-qwen3-tts"
            audio_plan["voiceProfileId"] = narration_report["voiceProfileId"]
            audio_plan["narrationAudio"] = narration_report["artifact"]
        scene_reports = []
        clip_paths = []
        for scene in project["scenes"]:
            source = Path(
                scene.get("videoStillPath")
                or scene.get("generatedImagePath", "")
            )
            if not source.exists():
                raise RuntimeError(f"Generated scene image is missing: {scene.get('id')}")
            camera_report = self.camera.plan(scene)
            motion_report = self.motion.plan(scene)
            talking_report = self.talking_head.plan(scene)
            lip_report = self.lip_sync.plan(scene, audio_available=bool(narration_report))
            clip_path = clip_dir / f"{scene['order']:02d}-{scene['id']}-v{scene.get('version', 1)}.mp4"
            generated_video = Path(scene.get("generatedVideoPath", ""))
            approved_video = Path(scene.get("sourceVideoPath", ""))
            video_source = generated_video if generated_video.is_file() else approved_video
            if video_source.is_file():
                subtitle_overlay = frame_dir / f"{scene['order']:02d}-{scene['id']}-subtitle-overlay.png"
                subtitle_report = self.subtitle.create_overlay(scene, subtitle_overlay)
                source_role = "wan22-generated-video" if generated_video.is_file() else "approved-source-video"
                render_report = self.renderer.render_video_clip(
                    video_source,
                    subtitle_overlay,
                    clip_path,
                    float(scene["duration"]),
                    source_role,
                    float(scene.get("sourceVideoStartSeconds", 0.0)),
                )
                root_source = str(
                    Path(
                        scene.get("videoProvenance", {}).get("sourceImage")
                        or video_source
                    ).resolve()
                )
            else:
                subtitle_frame = frame_dir / f"{scene['order']:02d}-{scene['id']}-subtitle.png"
                subtitle_report = self.subtitle.burn_frame(source, scene, subtitle_frame)
                render_report = self.renderer.render_clip(
                    subtitle_frame,
                    clip_path,
                    float(scene["duration"]),
                    camera_report,
                )
                root_source = str(
                    Path(
                        scene.get("visualProvenance", {}).get("videoStill")
                        or scene.get("visualProvenance", {}).get("sourceImage")
                        or source
                    ).resolve()
                )
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
                    "purpose": scene.get("purpose"),
                    "talkingHead": talking_report,
                    "lipSync": lip_report,
                    "motion": motion_report,
                    "camera": camera_report,
                    "subtitle": subtitle_report,
                    "render": render_report,
                    "quality": scene_quality,
                    "provenance": {
                        "rootSource": root_source,
                        "renderSource": render_report.get("source"),
                        "renderMode": render_report.get("renderMode"),
                        "visual": scene.get("visualProvenance", {}),
                    },
                }
            )
            clip_paths.append(clip_path)
        target = output_dir / ("preview.mp4" if preview else "final_video.mp4")
        concat_report = self.renderer.concat(clip_paths, target, video_dir)
        if concat_report["overall"] != "PASS":
            raise RuntimeError(f"Video concat failed: {concat_report.get('error', '')}")
        narration_mux = None
        if narration_report:
            narration_mux = self.renderer.mux_narration(
                target,
                Path(narration_report["artifact"]),
                target,
                sum(float(scene.get("duration", 0)) for scene in project["scenes"]),
            )
            if narration_mux["overall"] != "PASS":
                raise RuntimeError(
                    f"Narration mux failed: {narration_mux.get('error', '')}"
                )
        srt_path = output_dir / "subtitles.srt"
        srt_path.write_text(build_srt(project["scenes"]), encoding="utf-8-sig")
        if not preview:
            subtitled = output_dir / "final_video_subtitled.mp4"
            shutil.copyfile(target, subtitled)
        video_quality = self.quality.analyze(
            target,
            project["scenes"],
            scene_reports,
            narration_mux,
        )
        frame_quality_path = video_dir / (
            "frame-quality-preview.json" if preview else "frame-quality-final.json"
        )
        frame_quality = None
        if self.production_root:
            frame_quality = self.quality.analyze_frames(
                target,
                self.production_root,
                len(project["scenes"]),
                frame_quality_path,
            )
            video_quality = self.quality.merge_frame_analysis(video_quality, frame_quality)
        report = {
            "schema": VIDEO_INTELLIGENCE_SCHEMA,
            "version": VIDEO_INTELLIGENCE_VERSION,
            "createdAt": now_iso(),
            "projectId": project["id"],
            "provider": self.provider,
            "preview": preview,
            "generatedVideoEvidence": generated_video_evidence,
            "activeProviders": sorted(
                {
                    "ffmpeg-editorial-renderer",
                    *(
                        str(item.get("provider"))
                        for item in generated_video_evidence
                        if item.get("provider")
                    ),
                    *(
                        {"approved-emma-source-video"}
                        if any(
                            scene.get("sourceVideoPath")
                            for scene in project["scenes"]
                        )
                        else set()
                    ),
                }
            ),
            "narration": narration_report,
            "narrationMux": narration_mux,
            "audioSynchronization": audio_plan,
            "sceneReports": scene_reports,
            "concat": concat_report,
            "quality": video_quality,
            "frameQuality": frame_quality,
            "outputVideo": str(target),
            "subtitles": str(srt_path),
        }
        report_path = project_dir / ("video-intelligence-preview-report.json" if preview else "video-intelligence-final-report.json")
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report


def run_video_generation_pipeline(
    project: dict[str, Any],
    product: dict[str, Any],
    output_dir: Path,
    project_dir: Path,
    ffmpeg: Path,
    preview: bool = False,
    production_root: Path | None = None,
) -> dict[str, Any]:
    return VideoGenerationPipeline(ffmpeg, production_root=production_root).run(
        project,
        product,
        output_dir,
        project_dir,
        preview=preview,
    )


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
