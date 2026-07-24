from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from .emma_production import EmmaProductionActivator
from .provider_activation import NON_PRODUCTION_KINDS, ProviderActivationManager


ACCEPTANCE_VERSION = "1.0.0"
REQUIRED_SCENARIOS = {
    "product-introduction",
    "spiritual-content",
    "short-form-social",
    "emma-presenter",
    "talking-head",
    "mixed-product-emma",
    "alternate-format",
}
REQUIRED_STAGES = {
    "request",
    "research",
    "script",
    "storyboard",
    "emma",
    "image",
    "video",
    "voice",
    "lip-sync",
    "subtitle",
    "editing",
    "quality",
    "repair",
    "export",
}
AI_STAGES = {"research", "image", "video", "voice", "lip-sync", "quality"}
QUALITY_THRESHOLDS = {
    "emmaIdentity": 0.82,
    "emmaVoice": 0.82,
    "lipSync": 0.80,
    "visualQuality": 0.78,
    "subtitleQuality": 0.90,
    "productAccuracy": 0.90,
    "stability": 0.95,
    "commercialUsability": 0.80,
}
NON_PRODUCTION_PROVENANCE = {
    "mock",
    "simulator",
    "placeholder",
    "fake",
    "demo",
    "local-pil-commercial-composite-v1",
}


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def read_json(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8-sig"))


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def ffprobe_path(ffmpeg: str = "ffmpeg") -> str | None:
    executable = shutil.which(ffmpeg) or (ffmpeg if Path(ffmpeg).is_file() else None)
    if not executable:
        return None
    sibling = Path(executable).with_name("ffprobe.exe")
    return str(sibling) if sibling.is_file() else shutil.which("ffprobe")


def probe_media(path: Path, ffmpeg: str = "ffmpeg") -> dict[str, Any]:
    probe = ffprobe_path(ffmpeg)
    if not probe:
        return probe_media_with_ffmpeg(path, ffmpeg)
    if not Path(path).is_file():
        return {"overall": "FAIL", "reason": "media-not-found", "path": str(path)}
    result = subprocess.run(
        [
            probe,
            "-v",
            "error",
            "-show_entries",
            "format=duration,size,format_name:stream=codec_name,codec_type,width,height,r_frame_rate",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        return {"overall": "FAIL", "reason": result.stderr[-1000:], "path": str(path)}
    payload = json.loads(result.stdout)
    duration = float(payload.get("format", {}).get("duration", 0) or 0)
    video_streams = [
        stream for stream in payload.get("streams", []) if stream.get("codec_type") == "video"
    ]
    audio_streams = [
        stream for stream in payload.get("streams", []) if stream.get("codec_type") == "audio"
    ]
    return {
        "overall": "PASS" if duration > 0 and video_streams and audio_streams else "FAIL",
        "path": str(path),
        "durationSeconds": round(duration, 3),
        "videoStreams": video_streams,
        "audioStreams": audio_streams,
        "format": payload.get("format", {}),
    }


def probe_media_with_ffmpeg(path: Path, ffmpeg: str) -> dict[str, Any]:
    executable = shutil.which(ffmpeg) or (ffmpeg if Path(ffmpeg).is_file() else None)
    if not executable:
        return {"overall": "FAIL", "reason": "ffmpeg-not-found"}
    if not Path(path).is_file():
        return {"overall": "FAIL", "reason": "media-not-found", "path": str(path)}
    result = subprocess.run(
        [
            str(executable),
            "-hide_banner",
            "-i",
            str(path),
            "-f",
            "null",
            "NUL" if os.name == "nt" else "/dev/null",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
    )
    output = result.stdout + "\n" + result.stderr
    duration_match = re.search(
        r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)",
        output,
    )
    duration = 0.0
    if duration_match:
        duration = (
            int(duration_match.group(1)) * 3600
            + int(duration_match.group(2)) * 60
            + float(duration_match.group(3))
        )
    video_match = re.search(
        r"Stream\s+#\S+.*?Video:\s*([^,\s]+).*?(\d{2,5})x(\d{2,5})",
        output,
    )
    audio_match = re.search(r"Stream\s+#\S+.*?Audio:\s*([^,\s]+)", output)
    video_streams = (
        [
            {
                "codec_type": "video",
                "codec_name": video_match.group(1),
                "width": int(video_match.group(2)),
                "height": int(video_match.group(3)),
            }
        ]
        if video_match
        else []
    )
    audio_streams = (
        [{"codec_type": "audio", "codec_name": audio_match.group(1)}]
        if audio_match
        else []
    )
    return {
        "overall": "PASS"
        if result.returncode == 0 and duration > 0 and video_streams and audio_streams
        else "FAIL",
        "path": str(path),
        "durationSeconds": round(duration, 3),
        "videoStreams": video_streams,
        "audioStreams": audio_streams,
        "probe": "ffmpeg-decode",
        "returnCode": result.returncode,
        "errorTail": output[-1000:] if result.returncode else "",
    }


class CommercialAcceptanceSystem:
    def __init__(
        self,
        project_root: Path | str,
        production_root: Path | str,
    ):
        self.project_root = Path(project_root).resolve()
        self.root = Path(production_root).resolve()
        self.acceptance_root = self.root / "acceptance"
        self.runs_root = self.acceptance_root / "runs"
        self.report_path = self.acceptance_root / "final-acceptance-report.json"
        self.dashboard_path = self.acceptance_root / "final-acceptance-dashboard.html"
        self.emma = EmmaProductionActivator(
            self.project_root,
            self.root / "emma",
        )
        self.providers = ProviderActivationManager(self.root / "providers")

    def initialize(self) -> dict[str, Any]:
        self.runs_root.mkdir(parents=True, exist_ok=True)
        self.emma.initialize()
        self.providers.initialize()
        return self.readiness()

    def readiness(self) -> dict[str, Any]:
        emma = self.emma.status()
        providers = self.providers.status(run_health=False)
        blockers = []
        state = emma["state"]
        if not state.get("identityActivated"):
            blockers.append("Emma identity is not activated.")
        if not state.get("voiceActivated"):
            blockers.append("Emma voice is not activated.")
        required_capabilities = [
            "image",
            "video",
            "voice",
            "lip-sync",
            "rendering",
            "quality-video",
        ]
        selections = {
            capability: self.providers.select(
                capability,
                require_emma=capability in {"image", "video", "voice", "lip-sync"},
                dry_run=True,
            )
            for capability in required_capabilities
        }
        for capability, selection in selections.items():
            if not selection.get("selected"):
                blockers.append(f"No healthy production provider for {capability}.")
        return {
            "schema": "temple-ai-studio.final-activation-readiness.v1",
            "createdAt": now_iso(),
            "overall": "READY" if not blockers else "BLOCKED",
            "emma": emma,
            "providerSelections": selections,
            "blockers": blockers,
        }

    def evaluate(self, run_manifests: list[Path] | None = None) -> dict[str, Any]:
        self.initialize()
        if run_manifests is None:
            run_manifests = sorted(self.runs_root.glob("*/commercial-run.json"))
        readiness = self.readiness()
        runs = [self._evaluate_run(Path(path)) for path in run_manifests]
        scenario_types = {run.get("scenarioType") for run in runs if run.get("overall") == "PASS"}
        coverage = [
            {
                "scenarioType": scenario,
                "ok": scenario in scenario_types,
            }
            for scenario in sorted(REQUIRED_SCENARIOS)
        ]
        critical_failures = []
        if readiness["overall"] != "READY":
            critical_failures.extend(readiness["blockers"])
        if not all(item["ok"] for item in coverage):
            critical_failures.append("Representative commercial scenario coverage is incomplete.")
        failed_runs = [run for run in runs if run.get("overall") != "PASS"]
        if failed_runs:
            critical_failures.append(f"{len(failed_runs)} commercial runs failed.")
        report = {
            "schema": "temple-ai-studio.final-commercial-acceptance.v1",
            "version": ACCEPTANCE_VERSION,
            "createdAt": now_iso(),
            "overall": "PASS" if not critical_failures else "BLOCKED",
            "readiness": readiness,
            "coverage": coverage,
            "runs": runs,
            "statistics": self._statistics(runs),
            "criticalFailures": critical_failures,
            "commercialReleaseAllowed": not critical_failures,
        }
        atomic_write_json(self.report_path, report)
        self.dashboard_path.write_text(self._dashboard(report), encoding="utf-8")
        return report

    def _evaluate_run(self, manifest_path: Path) -> dict[str, Any]:
        manifest = read_json(manifest_path, {})
        errors = []
        scenario_type = manifest.get("scenarioType")
        if scenario_type not in REQUIRED_SCENARIOS:
            errors.append("unsupported-scenario")
        if manifest.get("requestLanguage") != "zh-TW":
            errors.append("request-language-must-be-zh-TW")
        stages = manifest.get("stages", {})
        missing_stages = sorted(REQUIRED_STAGES - set(stages))
        if missing_stages:
            errors.append("missing-stages:" + ",".join(missing_stages))
        for name, stage in stages.items():
            if stage.get("status") not in {"PASS", "SKIPPED_NOT_REQUIRED"}:
                errors.append(f"stage-failed:{name}")
            provenance = str(stage.get("provenance", "")).lower()
            provider_kind = str(stage.get("providerKind", "")).lower()
            if name in AI_STAGES and stage.get("status") != "SKIPPED_NOT_REQUIRED":
                if provenance != "real-production":
                    errors.append(f"non-production-provenance:{name}")
                if provider_kind in NON_PRODUCTION_KINDS:
                    errors.append(f"non-production-provider:{name}")
                provider_id = stage.get("providerId")
                try:
                    provider = self.providers.provider(provider_id)
                    if provider.get("kind") in NON_PRODUCTION_KINDS:
                        errors.append(f"registry-provider-not-production:{name}")
                except (KeyError, TypeError):
                    errors.append(f"unknown-provider:{name}")
        scores = manifest.get("qualityScores", {})
        for name, threshold in QUALITY_THRESHOLDS.items():
            value = scores.get(name)
            if not isinstance(value, (int, float)) or value < threshold:
                errors.append(f"quality-below-threshold:{name}")
        export_path = self._resolve_artifact(manifest_path, manifest.get("exportPath", ""))
        media = probe_media(export_path, manifest.get("ffmpeg", "ffmpeg"))
        if media["overall"] != "PASS":
            errors.append("export-not-playable")
        expected_aspect = manifest.get("aspectRatio")
        video_stream = media.get("videoStreams", [{}])[0] if media.get("videoStreams") else {}
        width = int(video_stream.get("width", 0) or 0)
        height = int(video_stream.get("height", 0) or 0)
        if expected_aspect == "9:16" and not (height > width):
            errors.append("aspect-ratio-mismatch")
        if expected_aspect == "16:9" and not (width > height):
            errors.append("aspect-ratio-mismatch")
        return {
            "manifest": str(manifest_path),
            "runId": manifest.get("runId"),
            "scenarioType": scenario_type,
            "overall": "PASS" if not errors else "FAIL",
            "errors": sorted(set(errors)),
            "qualityScores": scores,
            "durationSeconds": media.get("durationSeconds"),
            "generationSeconds": manifest.get("generationSeconds"),
            "costTwd": manifest.get("costTwd", 0.0),
            "media": media,
        }

    @staticmethod
    def _resolve_artifact(manifest_path: Path, value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else (manifest_path.parent / path).resolve()

    @staticmethod
    def _statistics(runs: list[dict[str, Any]]) -> dict[str, Any]:
        passed = [run for run in runs if run.get("overall") == "PASS"]
        generation_times = [
            float(run["generationSeconds"])
            for run in passed
            if isinstance(run.get("generationSeconds"), (int, float))
        ]
        return {
            "runCount": len(runs),
            "passCount": len(passed),
            "passRate": round(len(passed) / len(runs), 4) if runs else 0.0,
            "averageGenerationSeconds": round(sum(generation_times) / len(generation_times), 3)
            if generation_times
            else None,
            "totalCostTwd": round(sum(float(run.get("costTwd", 0) or 0) for run in runs), 2),
            "crashCount": sum(
                1
                for run in runs
                if any("crash" in error for error in run.get("errors", []))
            ),
        }

    def _dashboard(self, report: dict[str, Any]) -> str:
        status = report["overall"]
        color = "#146c43" if status == "PASS" else "#9a3412"
        coverage_rows = "".join(
            f"<tr><td>{item['scenarioType']}</td><td>{'PASS' if item['ok'] else 'BLOCKED'}</td></tr>"
            for item in report["coverage"]
        )
        run_rows = "".join(
            f"<tr><td>{run.get('scenarioType')}</td><td>{run.get('overall')}</td>"
            f"<td>{run.get('generationSeconds') or '-'}</td><td>{run.get('costTwd', 0)}</td></tr>"
            for run in report["runs"]
        )
        blockers = "".join(f"<li>{item}</li>" for item in report["criticalFailures"]) or "<li>None</li>"
        return f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Temple AI Studio 最終商業驗收</title>
<style>
body{{font-family:"Microsoft JhengHei",sans-serif;margin:32px;color:#18231f;background:#f7f7f4}}
main{{max-width:980px;margin:auto}}h1{{font-size:32px}}.status{{font-size:26px;color:{color};font-weight:700}}
section{{background:#fff;border:1px solid #d9ddd9;padding:20px;margin:16px 0;border-radius:6px}}
table{{width:100%;border-collapse:collapse}}th,td{{padding:10px;border-bottom:1px solid #ddd;text-align:left}}
</style>
</head>
<body><main>
<h1>Temple AI Studio 最終商業驗收</h1>
<p class="status">{status}</p>
<section><h2>阻塞項目</h2><ul>{blockers}</ul></section>
<section><h2>情境覆蓋</h2><table><tr><th>情境</th><th>狀態</th></tr>{coverage_rows}</table></section>
<section><h2>實際專案</h2><table><tr><th>情境</th><th>狀態</th><th>秒數</th><th>成本 TWD</th></tr>{run_rows}</table></section>
<p>產生時間：{report['createdAt']}</p>
</main></body></html>"""


class FinalReleaseManager:
    def __init__(self, project_root: Path | str, production_root: Path | str):
        self.project_root = Path(project_root).resolve()
        self.root = Path(production_root).resolve()
        self.acceptance = CommercialAcceptanceSystem(self.project_root, self.root)
        self.release_root = self.root / "releases"

    def create_release(self, version: str) -> dict[str, Any]:
        report = self.acceptance.evaluate()
        if report.get("overall") != "PASS":
            raise PermissionError("Final release is blocked until real commercial acceptance passes.")
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        package_root = self.release_root / f"Temple-AI-Studio-{version}"
        package_root.mkdir(parents=True, exist_ok=False)
        include = [
            "apps",
            "config",
            "docs",
            "knowledge",
            "prompts",
            "scripts",
            "README.md",
            ".gitignore",
            "install_temple_ai_studio.bat",
            "start_temple_ai_studio.bat",
            "stop_temple_ai_studio.bat",
        ]
        for relative in include:
            source = self.project_root / relative
            target = package_root / relative
            if source.is_dir():
                shutil.copytree(
                    source,
                    target,
                    ignore=shutil.ignore_patterns(
                        "data",
                        "release",
                        "__pycache__",
                        "*.pyc",
                        "*.log",
                        "*.mp4",
                        "*.wav",
                        "*.jpg",
                        "*.jpeg",
                        "*.png",
                        "*.safetensors",
                        "*.dpapi",
                    ),
                )
            elif source.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
        packaged_files = sorted(
            path
            for path in package_root.rglob("*")
            if path.is_file()
        )
        checksums = {}
        for path in packaged_files:
            digest = hashlib.sha256()
            with path.open("rb") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
            checksums[str(path.relative_to(package_root))] = digest.hexdigest()
        manifest = {
            "schema": "temple-ai-studio.final-release.v1",
            "version": version,
            "createdAt": now_iso(),
            "commercialAcceptanceReport": str(self.acceptance.report_path),
            "provenance": "real-production-accepted",
            "installer": "install_temple_ai_studio.bat",
            "launcher": "start_temple_ai_studio.bat",
            "files": sorted(
                [str(path.relative_to(package_root)) for path in packaged_files]
                + ["RELEASE_MANIFEST.json"]
            ),
            "sha256": checksums,
        }
        atomic_write_json(package_root / "RELEASE_MANIFEST.json", manifest)
        archive = self.release_root / f"Temple-AI-Studio-{version}-{stamp}.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
            for path in package_root.rglob("*"):
                if path.is_file():
                    output.write(path, Path(package_root.name) / path.relative_to(package_root))
        return {
            "overall": "PASS",
            "version": version,
            "portablePath": str(package_root),
            "archivePath": str(archive),
            "manifest": str(package_root / "RELEASE_MANIFEST.json"),
        }
