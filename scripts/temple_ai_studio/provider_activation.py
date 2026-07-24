from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from .secure_secrets import SecureSecretStore


PROVIDER_ACTIVATION_VERSION = "1.0.0"
NON_PRODUCTION_KINDS = {"mock", "simulator", "placeholder", "fake"}


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


def default_comfy_root() -> Path:
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    return local / "Comfy-Desktop" / "ComfyUI-Shared"


def default_comfy_install() -> Path:
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    return local / "Comfy-Desktop" / "ComfyUI-Installs" / "ComfyUI" / "ComfyUI"


def command_exists(command: str) -> bool:
    candidate = Path(command)
    return candidate.exists() if candidate.is_absolute() else shutil.which(command) is not None


def detect_ffmpeg() -> str:
    discovered = shutil.which("ffmpeg")
    if discovered:
        return discovered
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    candidates = [
        local
        / "Comfy-Desktop"
        / "ComfyUI-Installs"
        / "ComfyUI"
        / "ComfyUI"
        / ".venv"
        / "Lib"
        / "site-packages"
        / "imageio_ffmpeg"
        / "binaries"
        / "ffmpeg-win-x86_64-v7.1.exe",
        Path(r"C:\Program Files\Softdeluxe\Free Download Manager\ffmpeg.exe"),
        Path(r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"),
        Path(r"C:\ffmpeg\bin\ffmpeg.exe"),
    ]
    return str(next((path for path in candidates if path.is_file()), Path("ffmpeg")))


class ProviderActivationManager:
    def __init__(self, data_root: Path | str):
        self.root = Path(data_root).resolve()
        self.registry_path = self.root / "providers.json"
        self.ledger_path = self.root / "cost-ledger.json"
        self.health_path = self.root / "provider-health.json"
        self.secrets = SecureSecretStore(self.root / "secrets")

    def defaults(self) -> dict[str, Any]:
        comfy_root = default_comfy_root()
        comfy_install = default_comfy_install()
        return {
            "schema": "temple-ai-studio.production-providers.v1",
            "version": PROVIDER_ACTIVATION_VERSION,
            "updatedAt": now_iso(),
            "billing": {
                "enabled": False,
                "approvalReference": None,
                "monthlyLimitTwd": 0.0,
                "perJobLimitTwd": 0.0,
                "emergencyStop": True,
            },
            "selection": {
                "localFirst": True,
                "fallbackEnabled": True,
                "dryRun": True,
                "healthMaxAgeSeconds": 300,
            },
            "providers": [
                {
                    "id": "temple-knowledge-local",
                    "name": "Temple Local Knowledge",
                    "kind": "local-library",
                    "enabled": True,
                    "paid": False,
                    "capabilities": ["research"],
                    "priority": 100,
                    "quality": 0.8,
                    "stability": 0.95,
                    "privacy": "local",
                    "licensePolicy": "project-owned-content",
                    "path": str(self.root.parent / "knowledge"),
                },
                {
                    "id": "comfyui-local",
                    "name": "ComfyUI Local",
                    "kind": "local-http",
                    "enabled": True,
                    "paid": False,
                    "endpoint": "http://127.0.0.1:8188",
                    "healthPath": "/system_stats",
                    "capabilities": ["workflow-host"],
                    "priority": 100,
                    "quality": 0.82,
                    "stability": 0.82,
                    "privacy": "local",
                    "licensePolicy": "per-model",
                    "installPath": str(comfy_install),
                    "modelRoot": str(comfy_root / "models"),
                    "requiredModels": [],
                },
                {
                    "id": "qwen-image-edit-local",
                    "name": "Qwen Image Edit 2509 via ComfyUI",
                    "kind": "comfyui-workflow",
                    "enabled": True,
                    "paid": False,
                    "endpoint": "http://127.0.0.1:8188",
                    "healthPath": "/system_stats",
                    "capabilities": ["image", "identity"],
                    "priority": 95,
                    "quality": 0.86,
                    "stability": 0.8,
                    "privacy": "local",
                    "licensePolicy": "apache-2.0",
                    "modelRoot": str(comfy_root / "models"),
                    "requiredModels": [
                        "diffusion_models/qwen_image_edit_2509*.safetensors",
                        "text_encoders/qwen_2.5_vl_7b*.safetensors",
                        "vae/qwen_image_vae*.safetensors",
                        "loras/Qwen-Image-Edit-2509-Lightning-4steps*.safetensors",
                    ],
                    "workflowDescriptor": str(
                        self.root.parent / "workflows" / "qwen-image-edit-production.json"
                    ),
                },
                {
                    "id": "flux2-klein-local",
                    "name": "FLUX.2 Klein 4B via ComfyUI",
                    "kind": "comfyui-workflow",
                    "enabled": True,
                    "paid": False,
                    "endpoint": "http://127.0.0.1:8188",
                    "healthPath": "/system_stats",
                    "capabilities": ["image", "identity"],
                    "priority": 98,
                    "quality": 0.9,
                    "stability": 0.86,
                    "privacy": "local",
                    "licensePolicy": "apache-2.0",
                    "modelRoot": str(comfy_root / "models"),
                    "requiredModels": [
                        "diffusion_models/flux-2-klein-4b*.safetensors",
                        "text_encoders/qwen_3_4b*.safetensors",
                        "vae/flux2-vae*.safetensors",
                    ],
                    "workflowDescriptor": str(
                        self.root.parent / "workflows" / "flux2-klein-production.json"
                    ),
                },
                {
                    "id": "wan21-local",
                    "name": "Wan 2.1 via ComfyUI",
                    "kind": "comfyui-workflow",
                    "enabled": True,
                    "paid": False,
                    "endpoint": "http://127.0.0.1:8188",
                    "healthPath": "/system_stats",
                    "capabilities": ["video"],
                    "priority": 90,
                    "quality": 0.82,
                    "stability": 0.74,
                    "privacy": "local",
                    "licensePolicy": "apache-2.0",
                    "modelRoot": str(comfy_root / "models"),
                    "requiredModels": ["diffusion_models/wan2.1*.safetensors"],
                    "workflowDescriptor": str(
                        self.root.parent / "workflows" / "wan21-production.json"
                    ),
                },
                {
                    "id": "wan22-ti2v-local",
                    "name": "Wan 2.2 TI2V 5B via ComfyUI",
                    "kind": "comfyui-workflow",
                    "enabled": True,
                    "paid": False,
                    "endpoint": "http://127.0.0.1:8188",
                    "healthPath": "/system_stats",
                    "capabilities": ["video"],
                    "priority": 96,
                    "quality": 0.88,
                    "stability": 0.82,
                    "privacy": "local",
                    "licensePolicy": "apache-2.0",
                    "modelRoot": str(comfy_install / "models"),
                    "requiredModels": [
                        "diffusion_models/TI2V/Wan2_2-TI2V-5B*.safetensors",
                        "text_encoders/umt5-xxl-enc*.safetensors",
                        "vae/Wan2_2_VAE*.safetensors",
                    ],
                    "generation": {
                        "width": 480,
                        "height": 832,
                        "fps": 16,
                        "maxFrames": 49,
                    },
                    "workflowDescriptor": str(
                        self.root.parent / "workflows" / "wan22-ti2v-production.json"
                    ),
                },
                {
                    "id": "ltx23-local",
                    "name": "LTX 2.3 via ComfyUI",
                    "kind": "comfyui-workflow",
                    "enabled": True,
                    "paid": False,
                    "endpoint": "http://127.0.0.1:8188",
                    "healthPath": "/system_stats",
                    "capabilities": ["video", "audio-video"],
                    "priority": 88,
                    "quality": 0.86,
                    "stability": 0.78,
                    "privacy": "local",
                    "licensePolicy": "ltx-community-revenue-under-usd-10m",
                    "commercialDeclarationRequired": True,
                    "commercialDeclaration": None,
                    "modelRoot": str(comfy_root / "models"),
                    "requiredModels": [
                        "checkpoints/ltx-2.3*.safetensors",
                        "text_encoders/gemma_3_12B_it*.safetensors",
                        "latent_upscale_models/ltx-2.3-spatial-upscaler*.safetensors",
                        "loras/ltx-2.3-22b-distilled-lora-384.safetensors",
                    ],
                    "workflowDescriptor": str(
                        self.root.parent / "workflows" / "ltx23-production.json"
                    ),
                },
                {
                    "id": "qwen3-tts-local",
                    "name": "Qwen3-TTS 0.6B Base",
                    "kind": "local-python",
                    "enabled": True,
                    "paid": False,
                    "capabilities": ["voice", "tts", "voice-cloning"],
                    "priority": 100,
                    "quality": 0.88,
                    "stability": 0.82,
                    "privacy": "local",
                    "licensePolicy": "apache-2.0",
                    "python": str(self.root.parent / "runtimes" / "qwen3-tts" / "Scripts" / "python.exe"),
                    "modelPath": str(self.root.parent / "models" / "Qwen3-TTS-12Hz-0.6B-Base"),
                    "module": "qwen_tts",
                },
                {
                    "id": "musetalk-local",
                    "name": "MuseTalk 1.5 Local",
                    "kind": "local-script",
                    "enabled": True,
                    "paid": False,
                    "capabilities": ["lip-sync"],
                    "priority": 100,
                    "quality": 0.86,
                    "stability": 0.82,
                    "privacy": "local",
                    "licensePolicy": "mit-and-model-commercial",
                    "runtimePath": str(
                        self.root.parent / "runtimes" / "musetalk" / "Scripts" / "python.exe"
                    ),
                    "entryPoint": str(
                        self.root.parent / "tools" / "MuseTalk" / "scripts" / "inference.py"
                    ),
                    "modelRoot": str(self.root.parent / "models" / "musetalk"),
                    "requiredModels": ["**/*.pth"],
                    "commandDescriptor": str(
                        self.root.parent / "workflows" / "musetalk-production.json"
                    ),
                },
                {
                    "id": "latentsync15-local",
                    "name": "LatentSync 1.5 Local",
                    "kind": "local-script",
                    "enabled": True,
                    "paid": False,
                    "capabilities": ["lip-sync"],
                    "priority": 85,
                    "quality": 0.88,
                    "stability": 0.75,
                    "privacy": "local",
                    "licensePolicy": "apache-2.0",
                    "runtimePath": str(
                        self.root.parent / "runtimes" / "latentsync" / "Scripts" / "python.exe"
                    ),
                    "entryPoint": str(
                        self.root.parent / "tools" / "LatentSync" / "inference.py"
                    ),
                    "modelRoot": str(self.root.parent / "models" / "latentsync"),
                    "requiredModels": ["**/latentsync_unet.pt", "**/tiny.pt"],
                    "commandDescriptor": str(
                        self.root.parent / "workflows" / "latentsync-production.json"
                    ),
                },
                {
                    "id": "commercial-video-evaluator-local",
                    "name": "Commercial Video Quality Evaluator Local",
                    "kind": "local-script",
                    "enabled": True,
                    "paid": False,
                    "capabilities": ["quality-video"],
                    "priority": 100,
                    "quality": 0.88,
                    "stability": 0.85,
                    "privacy": "local",
                    "licensePolicy": "per-model",
                    "runtimePath": str(
                        self.root.parent
                        / "runtimes"
                        / "commercial-quality"
                        / "Scripts"
                        / "python.exe"
                    ),
                    "entryPoint": str(
                        self.root.parent
                        / "tools"
                        / "commercial-quality"
                        / "evaluate.py"
                    ),
                    "modelRoot": str(
                        self.root.parent / "models" / "commercial-quality"
                    ),
                    "requiredModels": ["**/syncnet*.pt", "**/open_clip*.safetensors"],
                    "commandDescriptor": str(
                        self.root.parent
                        / "workflows"
                        / "commercial-quality-production.json"
                    ),
                },
                {
                    "id": "ffmpeg-local",
                    "name": "FFmpeg Local",
                    "kind": "local-command",
                    "enabled": True,
                    "paid": False,
                    "capabilities": ["editing", "rendering", "subtitle", "audio-sync"],
                    "priority": 100,
                    "quality": 0.9,
                    "stability": 0.95,
                    "privacy": "local",
                    "licensePolicy": "installed-build",
                    "command": detect_ffmpeg(),
                },
                {
                    "id": "openai-paid",
                    "name": "OpenAI",
                    "kind": "cloud-api",
                    "enabled": False,
                    "paid": True,
                    "capabilities": ["llm", "image", "research"],
                    "priority": 50,
                    "quality": 0.9,
                    "stability": 0.9,
                    "privacy": "external",
                    "secretId": "openai-api-key",
                    "environmentName": "OPENAI_API_KEY",
                    "healthUrl": "https://api.openai.com/v1/models",
                    "authHeader": "Authorization",
                    "authPrefix": "Bearer ",
                },
                {
                    "id": "google-paid",
                    "name": "Google AI",
                    "kind": "cloud-api",
                    "enabled": False,
                    "paid": True,
                    "capabilities": ["llm", "image", "video", "research"],
                    "priority": 50,
                    "quality": 0.9,
                    "stability": 0.88,
                    "privacy": "external",
                    "secretId": "google-ai-api-key",
                    "environmentName": "GOOGLE_API_KEY",
                },
                {
                    "id": "runway-paid",
                    "name": "Runway",
                    "kind": "cloud-api",
                    "enabled": False,
                    "paid": True,
                    "capabilities": ["video", "lip-sync"],
                    "priority": 45,
                    "quality": 0.9,
                    "stability": 0.85,
                    "privacy": "external",
                    "secretId": "runway-api-key",
                    "environmentName": "RUNWAY_API_KEY",
                },
                {
                    "id": "kling-paid",
                    "name": "Kling",
                    "kind": "cloud-api",
                    "enabled": False,
                    "paid": True,
                    "capabilities": ["video", "lip-sync"],
                    "priority": 45,
                    "quality": 0.9,
                    "stability": 0.82,
                    "privacy": "external",
                    "secretId": "kling-api-key",
                    "environmentName": "KLING_API_KEY",
                },
            ],
        }

    def initialize(self) -> dict[str, Any]:
        self.root.mkdir(parents=True, exist_ok=True)
        self.secrets.initialize()
        if not self.registry_path.exists():
            atomic_write_json(self.registry_path, self.defaults())
        if not self.ledger_path.exists():
            atomic_write_json(
                self.ledger_path,
                {
                    "schema": "temple-ai-studio.provider-cost-ledger.v1",
                    "currency": "TWD",
                    "month": datetime.now().strftime("%Y-%m"),
                    "totalTwd": 0.0,
                    "entries": [],
                },
            )
        return self.status(run_health=False)

    def load(self) -> dict[str, Any]:
        self.initialize_files_only()
        current = read_json(self.registry_path, self.defaults())
        defaults = self.defaults()
        merged = {
            **defaults,
            **current,
            "billing": {**defaults["billing"], **current.get("billing", {})},
            "selection": {**defaults["selection"], **current.get("selection", {})},
        }
        current_by_id = {
            item.get("id"): item for item in current.get("providers", []) if item.get("id")
        }
        merged["providers"] = []
        for default_provider in defaults["providers"]:
            provider = {**default_provider, **current_by_id.get(default_provider["id"], {})}
            for policy_field in (
                "id",
                "kind",
                "paid",
                "capabilities",
                "privacy",
                "licensePolicy",
                "commercialDeclarationRequired",
                "secretId",
                "environmentName",
            ):
                if policy_field in default_provider:
                    provider[policy_field] = default_provider[policy_field]
                else:
                    provider.pop(policy_field, None)
            provider["requiredModels"] = list(
                dict.fromkeys(
                    default_provider.get("requiredModels", [])
                    + current_by_id.get(default_provider["id"], {}).get(
                        "requiredModels",
                        [],
                    )
                )
            )
            if (
                provider["id"] == "ffmpeg-local"
                and (
                    not command_exists(provider.get("command", ""))
                    or "Free Download Manager"
                    in str(provider.get("command", ""))
                )
            ):
                provider["command"] = detect_ffmpeg()
            merged["providers"].append(provider)
        known = {item["id"] for item in merged["providers"]}
        merged["providers"].extend(
            item for item in current.get("providers", []) if item.get("id") not in known
        )
        if merged != current:
            atomic_write_json(self.registry_path, merged)
        return merged

    def initialize_files_only(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        if not self.registry_path.exists():
            atomic_write_json(self.registry_path, self.defaults())
        if not self.ledger_path.exists():
            atomic_write_json(
                self.ledger_path,
                {
                    "schema": "temple-ai-studio.provider-cost-ledger.v1",
                    "currency": "TWD",
                    "month": datetime.now().strftime("%Y-%m"),
                    "totalTwd": 0.0,
                    "entries": [],
                },
            )

    def provider(self, provider_id: str) -> dict[str, Any]:
        item = next((item for item in self.load().get("providers", []) if item.get("id") == provider_id), None)
        if not item:
            raise KeyError(f"Unknown provider: {provider_id}")
        return item

    def save(self, registry: dict[str, Any]) -> None:
        registry["updatedAt"] = now_iso()
        atomic_write_json(self.registry_path, registry)

    def configure_provider(self, provider_id: str, changes: dict[str, Any]) -> dict[str, Any]:
        forbidden = {"secret", "apiKey", "token", "password"}
        if forbidden.intersection(changes):
            raise ValueError("Credentials must be stored with the secure secret store.")
        registry = self.load()
        provider = next((item for item in registry["providers"] if item["id"] == provider_id), None)
        if not provider:
            raise KeyError(f"Unknown provider: {provider_id}")
        if provider.get("paid") and changes.get("enabled") is True:
            billing = registry.get("billing", {})
            if (
                not billing.get("enabled")
                or billing.get("emergencyStop")
                or not billing.get("approvalReference")
                or billing.get("monthlyLimitTwd", 0) <= 0
                or billing.get("perJobLimitTwd", 0) <= 0
            ):
                raise PermissionError("Paid provider activation requires explicit CEO approval and spending limits.")
        provider.update(changes)
        self.save(registry)
        return self.redact_provider(provider)

    def store_secret(self, provider_id: str, value: str) -> dict[str, Any]:
        provider = self.provider(provider_id)
        secret_id = provider.get("secretId")
        if not secret_id:
            raise ValueError(f"Provider {provider_id} does not use an API secret.")
        return self.secrets.put(secret_id, value, provider.get("environmentName"))

    def authorize_billing(
        self,
        approval_reference: str,
        monthly_limit_twd: float,
        per_job_limit_twd: float,
    ) -> dict[str, Any]:
        if not approval_reference.strip():
            raise ValueError("CEO approval reference is required.")
        if monthly_limit_twd <= 0 or per_job_limit_twd <= 0:
            raise ValueError("Spending limits must be positive.")
        if per_job_limit_twd > monthly_limit_twd:
            raise ValueError("Per-job limit cannot exceed the monthly limit.")
        registry = self.load()
        registry["billing"] = {
            "enabled": True,
            "approvalReference": approval_reference.strip(),
            "approvedAt": now_iso(),
            "monthlyLimitTwd": round(float(monthly_limit_twd), 2),
            "perJobLimitTwd": round(float(per_job_limit_twd), 2),
            "emergencyStop": False,
        }
        self.save(registry)
        return dict(registry["billing"])

    def emergency_disable_billing(self) -> dict[str, Any]:
        registry = self.load()
        registry["billing"]["enabled"] = False
        registry["billing"]["emergencyStop"] = True
        registry["billing"]["disabledAt"] = now_iso()
        disabled = []
        for provider in registry.get("providers", []):
            if provider.get("paid"):
                provider["enabled"] = False
                disabled.append(provider["id"])
        self.save(registry)
        return {"overall": "PASS", "billingEnabled": False, "disabledProviders": disabled}

    def declare_commercial_eligibility(self, provider_id: str, declaration: str) -> dict[str, Any]:
        if not declaration.strip():
            raise ValueError("Commercial eligibility declaration is required.")
        return self.configure_provider(
            provider_id,
            {
                "commercialDeclaration": {
                    "statement": declaration.strip(),
                    "recordedAt": now_iso(),
                }
            },
        )

    def test_connection(self, provider_id: str, timeout: float = 3.0) -> dict[str, Any]:
        provider = self.provider(provider_id)
        started = time.perf_counter()
        kind = provider.get("kind")
        checks: list[dict[str, Any]] = []
        if kind in {"local-http", "comfyui-workflow"}:
            checks.extend(self._model_checks(provider))
            if kind == "comfyui-workflow":
                descriptor = Path(provider.get("workflowDescriptor", ""))
                checks.append(
                    {
                        "name": "production-workflow-descriptor",
                        "ok": descriptor.is_file(),
                        "path": str(descriptor),
                    }
                )
            url = provider["endpoint"].rstrip("/") + provider.get("healthPath", "/")
            try:
                with urllib.request.urlopen(url, timeout=timeout) as response:
                    checks.append({"name": "http", "ok": 200 <= response.status < 300, "status": response.status})
            except (OSError, urllib.error.URLError, TimeoutError) as error:
                checks.append({"name": "http", "ok": False, "reason": str(error)})
        else:
            try:
                if kind == "local-command":
                    command = provider.get("command", "")
                    exists = command_exists(command)
                    checks.append({"name": "command", "ok": exists, "command": command})
                    if exists:
                        result = subprocess.run(
                            [command, "-version"],
                            capture_output=True,
                            text=True,
                            timeout=timeout,
                            check=False,
                        )
                        checks.append({"name": "version", "ok": result.returncode == 0})
                        if provider.get("id") == "ffmpeg-local":
                            encoders = subprocess.run(
                                [command, "-hide_banner", "-encoders"],
                                capture_output=True,
                                text=True,
                                timeout=timeout,
                                check=False,
                            )
                            filters = subprocess.run(
                                [command, "-hide_banner", "-filters"],
                                capture_output=True,
                                text=True,
                                timeout=timeout,
                                check=False,
                            )
                            checks.extend(
                                [
                                    {
                                        "name": "h264-encoder",
                                        "ok": "libx264" in encoders.stdout
                                        or "h264_nvenc" in encoders.stdout
                                        or "h264_mf" in encoders.stdout,
                                    },
                                    {
                                        "name": "subtitle-burn-in",
                                        "ok": " subtitles " in filters.stdout
                                        or "\nsubtitles " in filters.stdout,
                                    },
                                ]
                            )
                elif kind == "local-python":
                    python = Path(provider.get("python", ""))
                    model = Path(provider.get("modelPath", ""))
                    checks.extend(
                        [
                            {"name": "python-runtime", "ok": python.exists(), "path": str(python)},
                            {"name": "model", "ok": model.exists(), "path": str(model)},
                        ]
                    )
                    if python.exists():
                        result = subprocess.run(
                            [str(python), "-c", f"import {provider.get('module', 'qwen_tts')}"],
                            capture_output=True,
                            text=True,
                            timeout=timeout,
                            check=False,
                        )
                        checks.append({"name": "python-module", "ok": result.returncode == 0})
                elif kind == "local-script":
                    runtime = Path(provider.get("runtimePath", ""))
                    entry_point = Path(provider.get("entryPoint", ""))
                    descriptor = Path(provider.get("commandDescriptor", ""))
                    checks.extend(
                        [
                            {
                                "name": "python-runtime",
                                "ok": runtime.is_file(),
                                "path": str(runtime),
                            },
                            {
                                "name": "entry-point",
                                "ok": entry_point.is_file(),
                                "path": str(entry_point),
                            },
                            {
                                "name": "production-command-descriptor",
                                "ok": descriptor.is_file(),
                                "path": str(descriptor),
                            },
                        ]
                    )
                    checks.extend(self._model_checks(provider))
                elif kind == "local-library":
                    library = Path(provider.get("path", ""))
                    files = list(library.rglob("*.json")) + list(
                        library.rglob("*.md")
                    ) if library.is_dir() else []
                    checks.append(
                        {
                            "name": "knowledge-library",
                            "ok": bool(files),
                            "path": str(library),
                            "fileCount": len(files),
                        }
                    )
                elif kind == "cloud-api":
                    secret = self.secrets.get(provider.get("secretId", ""), provider.get("environmentName"))
                    checks.append({"name": "secret", "ok": bool(secret)})
                    if secret and provider.get("healthUrl"):
                        request = urllib.request.Request(provider["healthUrl"])
                        request.add_header(
                            provider.get("authHeader", "Authorization"),
                            provider.get("authPrefix", "Bearer ") + secret,
                        )
                        with urllib.request.urlopen(request, timeout=timeout) as response:
                            checks.append({"name": "api", "ok": 200 <= response.status < 300, "status": response.status})
                else:
                    checks.append({"name": "production-kind", "ok": False, "reason": f"Unsupported provider kind: {kind}"})
            except (OSError, subprocess.SubprocessError, urllib.error.URLError, TimeoutError) as error:
                checks.append({"name": "connection", "ok": False, "reason": str(error)})
        if provider.get("commercialDeclarationRequired"):
            checks.append(
                {
                    "name": "commercial-declaration",
                    "ok": bool(provider.get("commercialDeclaration")),
                }
            )
        production_kind = kind not in NON_PRODUCTION_KINDS
        checks.append({"name": "production-provider", "ok": production_kind})
        result = {
            "providerId": provider_id,
            "checkedAt": now_iso(),
            "overall": "PASS" if checks and all(check["ok"] for check in checks) else "FAIL",
            "latencyMs": round((time.perf_counter() - started) * 1000, 2),
            "checks": checks,
        }
        health = read_json(self.health_path, {"schema": "temple-ai-studio.provider-health.v1", "providers": {}})
        health.setdefault("providers", {})[provider_id] = result
        health["updatedAt"] = now_iso()
        atomic_write_json(self.health_path, health)
        return result

    def test_all(self, include_disabled: bool = False) -> dict[str, Any]:
        registry = self.load()
        results = []
        for provider in registry.get("providers", []):
            if include_disabled or provider.get("enabled"):
                results.append(self.test_connection(provider["id"]))
        return {
            "schema": "temple-ai-studio.provider-health-summary.v1",
            "createdAt": now_iso(),
            "overall": "PASS" if any(item["overall"] == "PASS" for item in results) else "FAIL",
            "results": results,
        }

    def select(
        self,
        capability: str,
        estimated_cost_twd: float = 0.0,
        require_emma: bool = False,
        dry_run: bool | None = None,
    ) -> dict[str, Any]:
        registry = self.load()
        settings = registry.get("selection", {})
        dry_run = settings.get("dryRun", True) if dry_run is None else dry_run
        health = read_json(self.health_path, {"providers": {}}).get("providers", {})
        candidates = []
        rejected = []
        for provider in registry.get("providers", []):
            reason = self._provider_rejection(provider, capability, estimated_cost_twd, registry, health)
            if reason:
                rejected.append({"providerId": provider["id"], "reason": reason})
                continue
            score = (
                provider.get("priority", 0) / 100 * 0.25
                + provider.get("quality", 0) * 0.35
                + provider.get("stability", 0) * 0.25
                + (0.15 if provider.get("privacy") == "local" else 0)
            )
            if require_emma and capability in {"image", "video", "voice", "identity"}:
                score += 0.05 if "identity" in provider.get("capabilities", []) or "voice-cloning" in provider.get("capabilities", []) else -0.2
            candidates.append((score, provider))
        candidates.sort(key=lambda item: item[0], reverse=True)
        selected = self.redact_provider(candidates[0][1]) if candidates else None
        fallbacks = [self.redact_provider(item[1]) for item in candidates[1:]]
        return {
            "schema": "temple-ai-studio.provider-selection.v1",
            "createdAt": now_iso(),
            "capability": capability,
            "dryRun": bool(dry_run),
            "selected": selected,
            "fallbacks": fallbacks,
            "rejected": rejected,
            "estimatedCostTwd": round(float(estimated_cost_twd), 2),
            "requiresCEOApproval": not candidates and any(
                provider.get("paid") and capability in provider.get("capabilities", [])
                for provider in registry.get("providers", [])
            ),
        }

    def record_usage(self, provider_id: str, job_id: str, cost_twd: float) -> dict[str, Any]:
        if cost_twd < 0:
            raise ValueError("Cost cannot be negative.")
        registry = self.load()
        provider = self.provider(provider_id)
        if provider.get("paid"):
            self._assert_cost_allowed(float(cost_twd), registry)
        ledger = read_json(self.ledger_path, {"currency": "TWD", "month": "", "totalTwd": 0.0, "entries": []})
        current_month = datetime.now().strftime("%Y-%m")
        if ledger.get("month") != current_month:
            ledger = {
                "schema": "temple-ai-studio.provider-cost-ledger.v1",
                "currency": "TWD",
                "month": current_month,
                "totalTwd": 0.0,
                "entries": [],
            }
        entry = {
            "providerId": provider_id,
            "jobId": job_id,
            "costTwd": round(float(cost_twd), 2),
            "recordedAt": now_iso(),
        }
        ledger["entries"].append(entry)
        ledger["totalTwd"] = round(sum(item["costTwd"] for item in ledger["entries"]), 2)
        atomic_write_json(self.ledger_path, ledger)
        return entry

    def status(self, run_health: bool = False) -> dict[str, Any]:
        self.initialize_files_only()
        self.secrets.initialize()
        registry = self.load()
        if run_health:
            self.test_all()
        health = read_json(self.health_path, {"providers": {}})
        ledger = read_json(self.ledger_path, {"totalTwd": 0.0, "entries": []})
        return {
            "schema": "temple-ai-studio.provider-activation-status.v1",
            "version": PROVIDER_ACTIVATION_VERSION,
            "billing": registry.get("billing", {}),
            "selection": registry.get("selection", {}),
            "providers": [
                {
                    **self.redact_provider(provider),
                    "health": health.get("providers", {}).get(provider["id"], {}).get("overall", "NOT_TESTED"),
                    "secretConfigured": self._secret_configured(provider),
                }
                for provider in registry.get("providers", [])
            ],
            "monthlySpendTwd": ledger.get("totalTwd", 0.0),
            "secretStore": self.secrets.status(),
        }

    def _model_checks(self, provider: dict[str, Any]) -> list[dict[str, Any]]:
        root = Path(provider.get("modelRoot", ""))
        checks = []
        for pattern in provider.get("requiredModels", []):
            matches = list(root.glob(pattern)) if root.exists() else []
            checks.append(
                {
                    "name": f"model:{pattern}",
                    "ok": bool(matches),
                    "matches": [str(path) for path in matches[:3]],
                }
            )
        return checks

    def _provider_rejection(
        self,
        provider: dict[str, Any],
        capability: str,
        estimated_cost_twd: float,
        registry: dict[str, Any],
        health: dict[str, Any],
    ) -> str | None:
        if not provider.get("enabled"):
            return "disabled"
        if capability not in provider.get("capabilities", []):
            return "capability-not-supported"
        if provider.get("kind") in NON_PRODUCTION_KINDS:
            return "non-production-provider"
        if provider.get("commercialDeclarationRequired") and not provider.get("commercialDeclaration"):
            return "commercial-license-declaration-required"
        last_health = health.get(provider["id"])
        if not last_health or last_health.get("overall") != "PASS":
            return "health-check-not-passed"
        if provider.get("paid"):
            try:
                self._assert_cost_allowed(estimated_cost_twd, registry)
            except (PermissionError, ValueError) as error:
                return str(error)
            if not self._secret_configured(provider):
                return "api-secret-not-configured"
        return None

    def _assert_cost_allowed(self, cost_twd: float, registry: dict[str, Any]) -> None:
        billing = registry.get("billing", {})
        if not billing.get("enabled") or billing.get("emergencyStop"):
            raise PermissionError("paid-billing-disabled")
        if not billing.get("approvalReference"):
            raise PermissionError("ceo-approval-missing")
        if cost_twd > float(billing.get("perJobLimitTwd", 0)):
            raise PermissionError("per-job-spending-limit-exceeded")
        ledger = read_json(self.ledger_path, {"month": "", "totalTwd": 0.0})
        current_total = ledger.get("totalTwd", 0.0) if ledger.get("month") == datetime.now().strftime("%Y-%m") else 0.0
        if current_total + cost_twd > float(billing.get("monthlyLimitTwd", 0)):
            raise PermissionError("monthly-spending-limit-exceeded")

    def _secret_configured(self, provider: dict[str, Any]) -> bool:
        secret_id = provider.get("secretId")
        if not secret_id:
            return False
        return self.secrets.has(secret_id, provider.get("environmentName"))

    @staticmethod
    def redact_provider(provider: dict[str, Any]) -> dict[str, Any]:
        blocked = {"secret", "apiKey", "token", "password"}
        return {key: value for key, value in provider.items() if key not in blocked}
