from __future__ import annotations

import json
import shutil
import subprocess
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .commercial_acceptance import probe_media
from .emma_production import EmmaProductionActivator
from .production_evaluators import OpenCVSFaceEvaluator, WavLMSpeakerEvaluator
from .prompt_translation_engine import translate_prompts
from .provider_activation import ProviderActivationManager
from .real_providers import (
    ComfyUIProductionClient,
    LocalCommandProductionClient,
    ProviderExecutionError,
    Qwen3TTSProductionClient,
)
from .script_engine import generate_video_script_package
from .storyboard_engine import build_storyboard


WORKFLOW_VERSION = "1.0.0"
REQUIRED_CAPABILITIES = (
    "image",
    "video",
    "voice",
    "lip-sync",
    "rendering",
    "quality-video",
)


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def read_json(path: Path, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.is_file():
        return fallback or {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def first_artifact(result: dict[str, Any], media_types: set[str]) -> Path:
    for artifact in result.get("artifacts", []):
        if artifact.get("mediaType") in media_types:
            path = Path(artifact["path"])
            if path.is_file() and path.stat().st_size > 0:
                return path
    raise ProviderExecutionError(
        f"Provider returned no usable artifact of type {sorted(media_types)}."
    )


class ProductionWorkflowBlocked(RuntimeError):
    def __init__(self, report: dict[str, Any]):
        super().__init__("Production workflow preflight is blocked.")
        self.report = report


class FFmpegCommercialRenderer:
    def __init__(self, ffmpeg: Path | str):
        self.ffmpeg = Path(ffmpeg).resolve()
        if not self.ffmpeg.is_file():
            raise FileNotFoundError(str(self.ffmpeg))

    def finalize(
        self,
        clips: list[Path],
        scenes: list[dict[str, Any]],
        output_dir: Path,
        aspect_ratio: str,
    ) -> dict[str, Any]:
        if not clips:
            raise ValueError("At least one real scene clip is required.")
        output_dir.mkdir(parents=True, exist_ok=True)
        concat_file = output_dir / "scene-concat.txt"
        concat_file.write_text(
            "".join(
                f"file '{str(Path(path).resolve()).replace(chr(39), chr(39) * 2)}'\n"
                for path in clips
            ),
            encoding="utf-8",
        )
        joined = output_dir / "joined-scenes.mp4"
        join_command = [
            str(self.ffmpeg),
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-map_metadata",
            "-1",
            "-movflags",
            "+faststart",
            str(joined),
        ]
        self._run(join_command, output_dir / "ffmpeg-concat.log")
        srt = output_dir / "subtitles.zh-TW.srt"
        srt.write_text(self._build_srt(scenes), encoding="utf-8-sig")
        final = output_dir / "temple-commercial-final.mp4"
        width, height = (1080, 1920) if aspect_ratio == "9:16" else (1920, 1080)
        subtitle_path = self._subtitle_filter_path(srt)
        filter_graph = (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"subtitles=filename='{subtitle_path}':"
            "force_style='FontName=Microsoft JhengHei,FontSize=18,"
            "PrimaryColour=&H00FFFFFF,OutlineColour=&H00101010,"
            "BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=96'"
        )
        render_command = [
            str(self.ffmpeg),
            "-y",
            "-i",
            str(joined),
            "-vf",
            filter_graph,
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-map_metadata",
            "-1",
            "-movflags",
            "+faststart",
            str(final),
        ]
        self._run(render_command, output_dir / "ffmpeg-render.log")
        media = probe_media(final, str(self.ffmpeg))
        if media.get("overall") != "PASS":
            raise ProviderExecutionError(f"Final MP4 validation failed: {media}")
        return {
            "schema": "temple-ai-studio.ffmpeg-commercial-render.v1",
            "provider": "ffmpeg-local",
            "provenance": "real-production",
            "output": str(final),
            "subtitles": str(srt),
            "media": media,
        }

    @staticmethod
    def _build_srt(scenes: list[dict[str, Any]]) -> str:
        blocks = []
        cursor = 0.0
        for index, scene in enumerate(scenes, start=1):
            duration = max(0.5, float(scene.get("duration", 0) or 0))
            start = cursor
            cursor += duration
            blocks.append(
                f"{index}\n"
                f"{FFmpegCommercialRenderer._srt_time(start)} --> "
                f"{FFmpegCommercialRenderer._srt_time(cursor)}\n"
                f"{str(scene.get('subtitle', '')).strip()}\n"
            )
        return "\n".join(blocks)

    @staticmethod
    def _srt_time(seconds: float) -> str:
        milliseconds = int(round(seconds * 1000))
        hours, milliseconds = divmod(milliseconds, 3_600_000)
        minutes, milliseconds = divmod(milliseconds, 60_000)
        whole_seconds, milliseconds = divmod(milliseconds, 1000)
        return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d},{milliseconds:03d}"

    @staticmethod
    def _subtitle_filter_path(path: Path) -> str:
        normalized = path.resolve().as_posix()
        if len(normalized) > 1 and normalized[1] == ":":
            normalized = normalized[0] + "\\:" + normalized[2:]
        return normalized.replace("'", r"\'")

    @staticmethod
    def _run(command: list[str], log_path: Path) -> None:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=3600,
            check=False,
        )
        log_path.write_text(
            "COMMAND\n"
            + json.dumps(command, ensure_ascii=False)
            + "\n\nSTDOUT\n"
            + result.stdout
            + "\n\nSTDERR\n"
            + result.stderr,
            encoding="utf-8",
        )
        if result.returncode != 0:
            raise ProviderExecutionError(
                f"FFmpeg failed with code {result.returncode}; see {log_path}."
            )


class RealProductionWorkflow:
    """Strict production path. It never substitutes mock or simulator output."""

    def __init__(self, project_root: Path | str, production_root: Path | str):
        self.project_root = Path(project_root).resolve()
        self.production_root = Path(production_root).resolve()
        self.projects_root = self.production_root / "projects"
        self.providers = ProviderActivationManager(self.production_root / "providers")
        self.emma = EmmaProductionActivator(
            self.project_root,
            self.production_root / "emma",
        )

    def initialize(self) -> dict[str, Any]:
        self.projects_root.mkdir(parents=True, exist_ok=True)
        self.providers.initialize()
        self.emma.initialize()
        return self.preflight(run_health=False)

    def preflight(self, run_health: bool = True) -> dict[str, Any]:
        self.providers.initialize()
        self.emma.initialize()
        if run_health:
            self.providers.test_all()
        emma_status = self.emma.status()
        selections = {
            capability: self.providers.select(
                capability,
                require_emma=capability in {"image", "video", "voice", "lip-sync"},
                dry_run=False,
            )
            for capability in REQUIRED_CAPABILITIES
        }
        blockers = []
        state = emma_status.get("state", {})
        if not state.get("identityActivated"):
            blockers.append(
                {
                    "code": "emma-identity-not-active",
                    "message": "Emma 身分尚未完成真實素材驗證與啟用。",
                }
            )
        if not state.get("voiceActivated"):
            blockers.append(
                {
                    "code": "emma-voice-not-active",
                    "message": "Emma 聲音尚未完成真實素材驗證與啟用。",
                }
            )
        for capability, selection in selections.items():
            if not selection.get("selected"):
                blockers.append(
                    {
                        "code": f"provider-unavailable:{capability}",
                        "message": f"{capability} 尚無通過健康檢查的真實生產 Provider。",
                        "rejected": selection.get("rejected", []),
                    }
                )
        report = {
            "schema": "temple-ai-studio.real-production-preflight.v1",
            "version": WORKFLOW_VERSION,
            "createdAt": now_iso(),
            "overall": "PASS" if not blockers else "BLOCKED",
            "emma": emma_status,
            "providers": selections,
            "blockers": blockers,
        }
        atomic_write_json(self.production_root / "health" / "production-preflight.json", report)
        return report

    def run(self, request: dict[str, Any]) -> dict[str, Any]:
        preflight = self.preflight(run_health=True)
        if preflight["overall"] != "PASS":
            raise ProductionWorkflowBlocked(preflight)
        self._validate_request(request)
        run_id = request.get("runId") or (
            f"commercial-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        )
        run_root = self.projects_root / run_id
        run_root.mkdir(parents=True, exist_ok=False)
        started = time.perf_counter()
        manifest = {
            "schema": "temple-ai-studio.real-production-run.v1",
            "runId": run_id,
            "createdAt": now_iso(),
            "status": "RUNNING",
            "requestLanguage": "zh-TW",
            "request": request,
            "preflight": preflight,
            "stages": {},
        }
        self._save_manifest(run_root, manifest)
        try:
            product = request["product"]
            research = self._research_evidence(request)
            if research:
                atomic_write_json(run_root / "research-evidence.json", research)
            script = request.get("scriptPackage") or generate_video_script_package(
                product,
                {
                    "requirement": request["request"],
                    "duration": request.get("duration", 30),
                    "platform": request.get("platform", "Instagram Reels"),
                },
                run_id,
            )
            atomic_write_json(run_root / "script.json", script)
            self._stage(manifest, "request", "PASS", "local-input")
            self._stage(
                manifest,
                "research",
                "SKIPPED_NOT_REQUIRED"
                if not request.get("researchRequired")
                else "PASS",
                "real-production" if request.get("researchRequired") else "not-required",
                provider_id=research.get("providerId") if research else None,
                provider_kind=research.get("providerKind") if research else None,
            )
            self._stage(manifest, "script", script["quality"]["overall"], "local-rule-engine")
            storyboard = build_storyboard(script, product)
            atomic_write_json(run_root / "storyboard.json", storyboard)
            self._stage(
                manifest,
                "storyboard",
                storyboard["quality"]["overall"],
                "local-rule-engine",
            )
            prompts = translate_prompts(
                script,
                storyboard,
                product,
                providers=["comfyui", "flux", "wan", "ltx"],
            )
            atomic_write_json(run_root / "provider-prompts.json", prompts)
            self._stage(manifest, "emma", "PASS", "real-production")
            selections = {
                key: value["selected"] for key, value in preflight["providers"].items()
            }
            identity_reference = self._identity_reference(request)
            voice_reference, voice_reference_text = self._voice_reference(request)
            scene_results = []
            for scene in script["scenes"]:
                scene_results.append(
                    self._run_scene(
                        run_root,
                        scene,
                        prompts,
                        product,
                        selections,
                        identity_reference,
                        voice_reference,
                        voice_reference_text,
                        request,
                    )
                )
            self._record_provider_stage(manifest, "image", selections["image"])
            self._record_provider_stage(manifest, "video", selections["video"])
            self._record_provider_stage(manifest, "voice", selections["voice"])
            self._record_provider_stage(manifest, "lip-sync", selections["lip-sync"])
            self._stage(manifest, "subtitle", "PASS", "real-production", "ffmpeg-local", "local-command")
            renderer = FFmpegCommercialRenderer(selections["rendering"]["command"])
            rendering = renderer.finalize(
                [Path(item["lipSyncVideo"]) for item in scene_results],
                script["scenes"],
                run_root / "export",
                request.get("aspectRatio", "9:16"),
            )
            self._stage(manifest, "editing", "PASS", "real-production", "ffmpeg-local", "local-command")
            self._stage(manifest, "export", "PASS", "real-production", "ffmpeg-local", "local-command")
            quality_provider = selections["quality-video"]
            external_quality_path = run_root / "quality" / "commercial-quality.json"
            quality_values = {
                "inputVideo": rendering["output"],
                "subtitleFile": rendering["subtitles"],
                "productReferences": ";".join(
                    str(path) for path in self._material_paths(product)
                ),
                "identityReference": identity_reference,
                "outputJson": external_quality_path,
                "outputDir": external_quality_path.parent,
                "python": quality_provider.get("runtimePath", ""),
                "entryPoint": quality_provider.get("entryPoint", ""),
            }
            self._retry(
                "commercial-quality",
                lambda: LocalCommandProductionClient().run_descriptor(
                    Path(quality_provider["commandDescriptor"]),
                    quality_values,
                    external_quality_path.parent,
                ),
            )
            quality = self._quality_evidence(
                request,
                scene_results,
                identity_reference,
                voice_reference,
                rendering,
                external_quality_path,
            )
            atomic_write_json(run_root / "quality-evidence.json", quality)
            self._stage(
                manifest,
                "quality",
                quality["overall"],
                "real-production",
                quality_provider["id"],
                quality_provider["kind"],
            )
            self._stage(
                manifest,
                "repair",
                "PASS" if not quality.get("failedChecks") else "FAIL",
                "real-production",
            )
            if quality["overall"] != "PASS":
                raise ProviderExecutionError(
                    "Real output failed commercial quality validation."
                )
            manifest.update(
                {
                    "status": "COMPLETED",
                    "completedAt": now_iso(),
                    "generationSeconds": round(time.perf_counter() - started, 3),
                    "aspectRatio": request.get("aspectRatio", "9:16"),
                    "scenarioType": request["scenarioType"],
                    "exportPath": rendering["output"],
                    "qualityScores": quality["qualityScores"],
                    "costTwd": 0.0,
                    "ffmpeg": selections["rendering"]["command"],
                    "sceneResults": scene_results,
                }
            )
            self._save_manifest(run_root, manifest)
            commercial_manifest = run_root / "commercial-run.json"
            atomic_write_json(commercial_manifest, manifest)
            return manifest
        except Exception as error:
            manifest["status"] = "FAILED"
            manifest["failedAt"] = now_iso()
            manifest["error"] = {
                "type": error.__class__.__name__,
                "message": str(error),
            }
            self._save_manifest(run_root, manifest)
            raise

    def _run_scene(
        self,
        run_root: Path,
        scene: dict[str, Any],
        prompts: dict[str, Any],
        product: dict[str, Any],
        selections: dict[str, dict[str, Any]],
        identity_reference: Path,
        voice_reference: Path,
        voice_reference_text: str,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        scene_root = run_root / "scenes" / scene["id"]
        scene_root.mkdir(parents=True, exist_ok=True)
        prompt_record = next(
            item for item in prompts["scenes"] if item["sceneId"] == scene["id"]
        )
        image_provider = selections["image"]
        image_prompt_key = (
            "flux" if image_provider["id"] == "flux2-klein-local" else "comfyui"
        )
        image_prompt = prompt_record["providers"][image_prompt_key]
        reference_images = self._material_paths(product)
        comfy = ComfyUIProductionClient(image_provider["endpoint"])
        uploaded_reference = (
            comfy.upload_image(reference_images[0])["comfyPath"]
            if reference_images
            else ""
        )
        seed = abs(hash((run_root.name, scene["id"], scene.get("version", 1)))) % 2_147_483_647
        image_result = self._retry(
            "image",
            lambda: comfy.run_descriptor(
                Path(image_provider["workflowDescriptor"]),
                {
                    "prompt": image_prompt["positive"],
                    "negative_prompt": image_prompt["negative"],
                    "seed": seed,
                    "width": 1080,
                    "height": 1920,
                    "reference_image": uploaded_reference,
                    "identity_reference": uploaded_reference,
                    "output_prefix": f"{run_root.name}-{scene['id']}-image",
                },
                scene_root / "image",
            ),
        )
        image_path = first_artifact(image_result, {"images", "image"})
        video_provider = selections["video"]
        video_prompt_key = "ltx" if video_provider["id"] == "ltx23-local" else "wan"
        video_prompt = prompt_record["providers"][video_prompt_key]
        video_comfy = ComfyUIProductionClient(video_provider["endpoint"])
        uploaded_frame = video_comfy.upload_image(image_path)["comfyPath"]
        generation = video_provider.get("generation", {})
        video_fps = int(generation.get("fps", 25))
        max_frames = int(generation.get("maxFrames", 0))
        num_frames = max(1, round(float(scene["duration"]) * video_fps) + 1)
        if max_frames > 0:
            num_frames = min(num_frames, max_frames)
        video_result = self._retry(
            "video",
            lambda: video_comfy.run_descriptor(
                Path(video_provider["workflowDescriptor"]),
                {
                    "prompt": video_prompt["positive"],
                    "negative_prompt": video_prompt["negative"],
                    "seed": seed,
                    "width": int(generation.get("width", 1080)),
                    "height": int(generation.get("height", 1920)),
                    "duration": scene["duration"],
                    "fps": video_fps,
                    "num_frames": num_frames,
                    "first_frame": uploaded_frame,
                    "reference_image": uploaded_frame,
                    "output_prefix": f"{run_root.name}-{scene['id']}-video",
                },
                scene_root / "video",
            ),
        )
        video_path = first_artifact(video_result, {"videos", "video", "gifs"})
        voice_provider = selections["voice"]
        tts = Qwen3TTSProductionClient(
            Path(voice_provider["python"]),
            self.project_root / "scripts" / "qwen3_tts_worker.py",
            Path(voice_provider["modelPath"]),
        )
        voice_output = scene_root / "voice" / "narration.wav"
        voice_result = self._retry(
            "voice",
            lambda: tts.synthesize(
                scene["narration"],
                voice_reference,
                voice_reference_text,
                voice_output,
            ),
        )
        lip_provider = selections["lip-sync"]
        lip_output = scene_root / "lip-sync" / "lip-synced.mp4"
        lip_values = {
            "inputVideo": video_path,
            "inputAudio": voice_output,
            "outputVideo": lip_output,
            "outputDir": lip_output.parent,
            "python": lip_provider.get("runtimePath", ""),
            "entryPoint": lip_provider.get("entryPoint", ""),
        }
        lip_result = self._retry(
            "lip-sync",
            lambda: LocalCommandProductionClient().run_descriptor(
                Path(lip_provider["commandDescriptor"]),
                lip_values,
                lip_output.parent,
            ),
        )
        lip_video = first_artifact(lip_result, {"videos", "video"})
        return {
            "sceneId": scene["id"],
            "seed": seed,
            "imageProvider": image_provider["id"],
            "videoProvider": video_provider["id"],
            "voiceProvider": voice_provider["id"],
            "lipSyncProvider": lip_provider["id"],
            "image": str(image_path),
            "video": str(video_path),
            "voice": voice_result["artifact"],
            "lipSyncVideo": str(lip_video),
            "provenance": "real-production",
        }

    def _quality_evidence(
        self,
        request: dict[str, Any],
        scene_results: list[dict[str, Any]],
        identity_reference: Path,
        voice_reference: Path,
        rendering: dict[str, Any],
        external_quality_path: Path,
    ) -> dict[str, Any]:
        evaluator_root = self.production_root / "models" / "evaluators"
        face = OpenCVSFaceEvaluator(
            evaluator_root / "face_detection_yunet_2023mar.onnx",
            evaluator_root / "face_recognition_sface_2021dec.onnx",
        )
        voice = WavLMSpeakerEvaluator(
            evaluator_root / "microsoft-wavlm-base-plus-sv"
        )
        checks = []
        identity_scores = []
        voice_scores = []
        for result in scene_results:
            frame = Path(result["image"])
            identity = face.compare(identity_reference, frame)
            speaker = voice.compare(voice_reference, Path(result["voice"]))
            checks.extend([identity, speaker])
            identity_scores.append(float(identity["score"]))
            voice_scores.append(float(speaker["score"]))
        external = read_json(external_quality_path)
        if external.get("provenance") != "real-production":
            raise ProviderExecutionError(
                "Lip-sync and commercial quality evidence must use real-production provenance."
            )
        required = {
            "lipSync",
            "visualQuality",
            "subtitleQuality",
            "productAccuracy",
            "commercialUsability",
        }
        scores = external.get("scores", {})
        missing = sorted(required - set(scores))
        if missing:
            raise ProviderExecutionError(
                f"Quality evidence is missing scores: {', '.join(missing)}"
            )
        quality_scores = {
            "emmaIdentity": min(1.0, min(identity_scores) / 0.363)
            if identity_scores
            else 0.0,
            "emmaVoice": min(voice_scores) if voice_scores else 0.0,
            "lipSync": float(scores["lipSync"]),
            "visualQuality": float(scores["visualQuality"]),
            "subtitleQuality": float(scores["subtitleQuality"]),
            "productAccuracy": float(scores["productAccuracy"]),
            "stability": 1.0 if rendering["media"]["overall"] == "PASS" else 0.0,
            "commercialUsability": float(scores["commercialUsability"]),
        }
        thresholds = {
            "emmaIdentity": 0.82,
            "emmaVoice": 0.82,
            "lipSync": 0.80,
            "visualQuality": 0.78,
            "subtitleQuality": 0.90,
            "productAccuracy": 0.90,
            "stability": 0.95,
            "commercialUsability": 0.80,
        }
        failed = [
            name for name, threshold in thresholds.items() if quality_scores[name] < threshold
        ]
        return {
            "schema": "temple-ai-studio.real-production-quality.v1",
            "createdAt": now_iso(),
            "overall": "PASS" if not failed else "FAIL",
            "provenance": "real-production",
            "qualityScores": quality_scores,
            "failedChecks": failed,
            "identityAndVoiceChecks": checks,
            "externalEvidence": str(external_quality_path.resolve()),
            "media": rendering["media"],
        }

    def _voice_reference(self, request: dict[str, Any]) -> tuple[Path, str]:
        if request.get("voiceReference") and request.get("voiceReferenceText"):
            return Path(request["voiceReference"]).resolve(), str(
                request["voiceReferenceText"]
            ).strip()
        state = self.emma.status()["state"]
        active = state.get("activeVersion")
        version = read_json(self.emma.versions / f"{active}.json")
        profile = read_json(Path(version.get("voiceProfile", "")))
        audio = Path(profile.get("referenceAudio", ""))
        text = str(profile.get("referenceText", "")).strip()
        if not audio.is_file() or not text:
            raise ProductionWorkflowBlocked(
                {
                    "overall": "BLOCKED",
                    "blockers": [
                        {
                            "code": "emma-voice-reference-missing",
                            "message": "Emma 生產聲音設定缺少參考 WAV 或逐字稿。",
                        }
                    ],
                }
            )
        return audio.resolve(), text

    @staticmethod
    def _material_paths(product: dict[str, Any]) -> list[Path]:
        paths = []
        for item in product.get("materials", []):
            raw = item.get("path") or item.get("filePath")
            if raw and Path(raw).is_file():
                paths.append(Path(raw).resolve())
        return paths

    @staticmethod
    def _validate_request(request: dict[str, Any]) -> None:
        required = {
            "request",
            "product",
            "scenarioType",
        }
        missing = sorted(required - set(request))
        if missing:
            raise ValueError(f"Missing production request fields: {', '.join(missing)}")
        if not str(request["request"]).strip():
            raise ValueError("Traditional Chinese request cannot be empty.")
        if request.get("aspectRatio", "9:16") not in {"9:16", "16:9"}:
            raise ValueError("Aspect ratio must be 9:16 or 16:9.")

    def _identity_reference(self, request: dict[str, Any]) -> Path:
        supplied = request.get("identityReference")
        if supplied and Path(supplied).is_file():
            return Path(supplied).resolve()
        status = self.emma.status()
        active = status.get("state", {}).get("activeVersion")
        version = read_json(self.emma.versions / f"{active}.json")
        preparation = version.get("preparation", {})
        dataset_path = Path(
            preparation.get("identity", {})
            .get("training", {})
            .get("datasetPath", "")
        )
        candidates = []
        if dataset_path.is_dir():
            for suffix in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
                candidates.extend(dataset_path.rglob(suffix))
        if not candidates:
            raise ProductionWorkflowBlocked(
                {
                    "overall": "BLOCKED",
                    "blockers": [
                        {
                            "code": "emma-identity-reference-missing",
                            "message": "Emma 生產版本找不到已核准的身分參考照片。",
                        }
                    ],
                }
            )
        return sorted(candidates)[0].resolve()

    @staticmethod
    def _retry(
        stage: str,
        operation: Callable[[], dict[str, Any]],
        attempts: int = 3,
    ) -> dict[str, Any]:
        errors = []
        for attempt in range(1, attempts + 1):
            try:
                return operation()
            except (ProviderExecutionError, TimeoutError, OSError) as error:
                errors.append(
                    {
                        "attempt": attempt,
                        "type": error.__class__.__name__,
                        "message": str(error),
                    }
                )
                if attempt < attempts:
                    time.sleep(min(2**attempt, 8))
        raise ProviderExecutionError(
            f"{stage} failed after {attempts} attempts: {json.dumps(errors, ensure_ascii=False)}"
        )

    @staticmethod
    def _stage(
        manifest: dict[str, Any],
        name: str,
        status: str,
        provenance: str,
        provider_id: str | None = None,
        provider_kind: str | None = None,
    ) -> None:
        manifest["stages"][name] = {
            "status": status,
            "provenance": provenance,
            "providerId": provider_id,
            "providerKind": provider_kind,
            "recordedAt": now_iso(),
        }

    def _record_provider_stage(
        self,
        manifest: dict[str, Any],
        name: str,
        provider: dict[str, Any],
    ) -> None:
        self._stage(
            manifest,
            name,
            "PASS",
            "real-production",
            provider["id"],
            provider["kind"],
        )

    def _research_evidence(self, request: dict[str, Any]) -> dict[str, Any] | None:
        if not request.get("researchRequired"):
            return None
        evidence_path = Path(str(request.get("researchEvidence", "")))
        if not evidence_path.is_file():
            raise ProviderExecutionError(
                "Research was requested but no real research evidence file was supplied."
            )
        evidence = read_json(evidence_path)
        sources = evidence.get("sources", [])
        if (
            evidence.get("provenance") != "real-production"
            or not isinstance(sources, list)
            or not sources
            or any(
                not str(item.get("title", "")).strip()
                or not str(item.get("source", "")).strip()
                or not str(item.get("finding", "")).strip()
                for item in sources
            )
        ):
            raise ProviderExecutionError(
                "Research evidence must contain real-production provenance and complete sources."
            )
        return {
            "schema": "temple-ai-studio.research-evidence.v1",
            "provenance": "real-production",
            "providerId": evidence.get("providerId", "temple-knowledge-local"),
            "providerKind": evidence.get("providerKind", "local-library"),
            "sources": sources,
            "summary": str(evidence.get("summary", "")).strip(),
        }

    @staticmethod
    def _save_manifest(run_root: Path, manifest: dict[str, Any]) -> None:
        atomic_write_json(run_root / "run-manifest.json", manifest)
