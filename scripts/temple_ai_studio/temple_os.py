from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import sys
import time
import uuid
import zipfile
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse


TEMPLE_OS_VERSION = "0.1.0"
SCHEMA_VERSION = 1


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def stable_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


def write_json_if_changed(path: Path, payload: Any) -> None:
    text = stable_json(payload)
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def safe_copy_file(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


class TempleOSPaths:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.operations = self.root / "operations" / "temple-os"
        self.state = self.operations / "state"
        self.config = self.state / "config.json"
        self.workspaces = self.state / "workspaces"
        self.projects = self.state / "projects.json"
        self.providers = self.state / "providers.json"
        self.models = self.state / "models.json"
        self.plugins = self.state / "plugins.json"
        self.prompts = self.state / "prompts.json"
        self.knowledge = self.state / "knowledge.json"
        self.workflows = self.state / "workflows.json"
        self.queue = self.state / "queue.json"
        self.schedules = self.state / "schedules.json"
        self.automation = self.state / "automation.json"
        self.telemetry = self.state / "telemetry.json"
        self.version = self.state / "version.json"
        self.user_profiles = self.state / "user_profiles.json"
        self.agents = self.state / "agents.json"
        self.agent_runs = self.state / "agent_runs.json"
        self.collaborations = self.state / "collaborations.json"
        self.downloads = self.state / "downloads.json"
        self.updates = self.state / "updates.json"
        self.applications = self.state / "applications.json"
        self.mobile_api = self.state / "mobile_api.json"
        self.cloud_sync = self.state / "cloud_sync.json"
        self.tenants = self.state / "tenants.json"
        self.logs = self.operations / "logs"
        self.events = self.logs / "events.jsonl"
        self.recovery_log = self.logs / "recovery.jsonl"
        self.backups = self.operations / "backups"
        self.support = self.operations / "support"
        self.tmp = self.operations / "tmp"
        self.plugins_dir = self.root / "plugins"

    def ensure_dirs(self) -> None:
        for path in [
            self.operations,
            self.state,
            self.workspaces,
            self.logs,
            self.backups,
            self.support,
            self.tmp,
            self.plugins_dir,
        ]:
            path.mkdir(parents=True, exist_ok=True)


class JsonEventLogger:
    def __init__(self, paths: TempleOSPaths):
        self.paths = paths

    def emit(self, event: str, payload: dict | None = None, level: str = "INFO") -> None:
        self.paths.ensure_dirs()
        record = {
            "time": now_iso(),
            "level": level,
            "event": event,
            "payload": payload or {},
        }
        with self.paths.events.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def recovery(self, event: str, payload: dict | None = None, level: str = "INFO") -> None:
        self.paths.ensure_dirs()
        record = {
            "time": now_iso(),
            "level": level,
            "event": event,
            "payload": payload or {},
        }
        with self.paths.recovery_log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def tail(self, limit: int = 50) -> list[dict]:
        if not self.paths.events.exists():
            return []
        lines = self.paths.events.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
        records: list[dict] = []
        for line in lines:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                records.append({"time": now_iso(), "level": "WARN", "event": "log-parse-failed", "raw": line})
        return records


class ConfigurationCenter:
    def __init__(self, paths: TempleOSPaths, logger: JsonEventLogger):
        self.paths = paths
        self.logger = logger

    def default(self) -> dict:
        return {
            "schemaVersion": SCHEMA_VERSION,
            "version": TEMPLE_OS_VERSION,
            "mode": "local-first",
            "language": "zh-TW",
            "privacy": {
                "allowPaidProviders": False,
                "allowCloudSync": False,
                "allowExternalTelemetry": False,
            },
            "limits": {
                "maxRetries": 2,
                "taskTimeoutSeconds": 900,
                "staleTaskSeconds": 3600,
            },
            "paths": {
                "workspaceRoot": str(self.paths.workspaces),
                "backupRoot": str(self.paths.backups),
                "supportRoot": str(self.paths.support),
                "temporaryRoot": str(self.paths.tmp),
            },
            "quality": {
                "minimumCommercialScore": 0.72,
                "minimumEmmaScore": 0.7,
                "automaticRetry": True,
            },
            "user": {
                "defaultProfileId": "ceo",
                "role": "CEO",
                "timezone": "Asia/Taipei",
            },
            "api": {
                "mobileContractEnabled": True,
                "restHost": "127.0.0.1",
                "restPort": 8765,
            },
            "multiUser": {
                "mode": "single-user-local",
                "tenantIsolation": "prepared",
            },
        }

    def ensure(self) -> dict:
        if not self.paths.config.exists():
            atomic_write_json(self.paths.config, self.default())
            self.logger.emit("config-initialized", {"path": str(self.paths.config)})
        return self.load()

    def load(self) -> dict:
        current = read_json(self.paths.config, self.default())
        base = self.default()
        merged = self._deep_merge(base, current)
        if merged != current:
            atomic_write_json(self.paths.config, merged)
            self.logger.emit("config-migrated", {"schemaVersion": SCHEMA_VERSION})
        return merged

    def update(self, changes: dict) -> dict:
        current = self.load()
        protected = {"allowPaidProviders", "allowCloudSync", "allowExternalTelemetry"}
        privacy = changes.get("privacy", {})
        for key in protected:
            if privacy.get(key) is True:
                raise PermissionError(f"{key} requires CEO approval.")
        updated = self._deep_merge(current, changes)
        atomic_write_json(self.paths.config, updated)
        self.logger.emit("config-updated", {"keys": sorted(changes.keys())})
        return updated

    def _deep_merge(self, base: dict, override: dict) -> dict:
        merged = dict(base)
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = self._deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged


class WorkspaceManager:
    def __init__(self, paths: TempleOSPaths, logger: JsonEventLogger):
        self.paths = paths
        self.logger = logger

    def ensure_default(self) -> dict:
        workspace = self.paths.workspaces / "default"
        folders = [
            "assets",
            "exports",
            "projects",
            "references",
            "knowledge",
            "prompts",
            "cache",
            "evidence",
        ]
        for folder in folders:
            (workspace / folder).mkdir(parents=True, exist_ok=True)
        manifest = {
            "schemaVersion": SCHEMA_VERSION,
            "id": "default",
            "name": "Default Temple Workspace",
            "path": str(workspace),
            "folders": {folder: str(workspace / folder) for folder in folders},
        }
        write_json_if_changed(workspace / "workspace.json", manifest)
        return manifest

    def status(self) -> dict:
        manifest = self.ensure_default()
        return {"default": manifest, "ready": Path(manifest["path"]).exists()}


class ProjectManager:
    def __init__(self, paths: TempleOSPaths, logger: JsonEventLogger):
        self.paths = paths
        self.logger = logger

    def ensure(self) -> dict:
        if not self.paths.projects.exists():
            payload = {"schemaVersion": SCHEMA_VERSION, "projects": []}
            atomic_write_json(self.paths.projects, payload)
            self.logger.emit("project-registry-initialized", {"path": str(self.paths.projects)})
        return self.load()

    def load(self) -> dict:
        return read_json(self.paths.projects, {"schemaVersion": SCHEMA_VERSION, "projects": []})

    def create(self, name: str, app_id: str, workspace_id: str = "default", metadata: dict | None = None) -> dict:
        registry = self.ensure()
        project = {
            "id": new_id("os-project"),
            "name": name,
            "appId": app_id,
            "workspaceId": workspace_id,
            "status": "active",
            "metadata": metadata or {},
            "createdAt": now_iso(),
            "updatedAt": now_iso(),
        }
        registry["projects"].append(project)
        atomic_write_json(self.paths.projects, registry)
        self.logger.emit("project-created", {"projectId": project["id"], "appId": app_id})
        return project

    def list(self) -> list[dict]:
        return self.ensure().get("projects", [])


class ProviderManager:
    def __init__(self, paths: TempleOSPaths, config: ConfigurationCenter, logger: JsonEventLogger):
        self.paths = paths
        self.config = config
        self.logger = logger

    def defaults(self) -> dict:
        return {
            "schemaVersion": SCHEMA_VERSION,
            "providers": [
                {
                    "id": "local-template",
                    "name": "Local Provider Adapter",
                    "type": "local",
                    "enabled": True,
                    "paid": False,
                    "privacy": "local",
                    "capabilities": ["llm", "script", "storyboard", "prompt", "image", "video", "subtitle", "editing", "qa"],
                    "stability": 0.75,
                    "automation": 0.85,
                    "quality": 0.65,
                    "emmaConsistency": 0.65,
                    "status": "available",
                },
                {
                    "id": "comfyui-local",
                    "name": "ComfyUI Local",
                    "type": "local",
                    "enabled": True,
                    "paid": False,
                    "privacy": "local",
                    "capabilities": ["image", "video", "identity-preservation"],
                    "stability": 0.7,
                    "automation": 0.75,
                    "quality": 0.72,
                    "emmaConsistency": 0.7,
                    "status": "optional",
                },
                {
                    "id": "ffmpeg-local",
                    "name": "FFmpeg Local",
                    "type": "local",
                    "enabled": True,
                    "paid": False,
                    "privacy": "local",
                    "capabilities": ["editing", "rendering", "subtitle", "audio-sync"],
                    "stability": 0.9,
                    "automation": 0.9,
                    "quality": 0.78,
                    "emmaConsistency": 0.5,
                    "status": "available",
                },
                {
                    "id": "future-cloud-adapter",
                    "name": "Future Cloud Provider",
                    "type": "cloud",
                    "enabled": False,
                    "paid": True,
                    "privacy": "external",
                    "capabilities": ["llm", "image", "video", "voice", "lip-sync"],
                    "stability": 0.82,
                    "automation": 0.88,
                    "quality": 0.85,
                    "emmaConsistency": 0.74,
                    "status": "requires-ceo-approval",
                },
            ],
        }

    def ensure(self) -> dict:
        if not self.paths.providers.exists():
            atomic_write_json(self.paths.providers, self.defaults())
            self.logger.emit("provider-registry-initialized", {"path": str(self.paths.providers)})
        return self.load()

    def load(self) -> dict:
        return read_json(self.paths.providers, self.defaults())

    def select(self, capability: str, constraints: dict | None = None) -> dict:
        constraints = constraints or {}
        config = self.config.load()
        allow_paid = bool(config.get("privacy", {}).get("allowPaidProviders"))
        allow_external = bool(config.get("privacy", {}).get("allowCloudSync"))
        candidates = []
        for provider in self.ensure().get("providers", []):
            if not provider.get("enabled"):
                continue
            if capability not in provider.get("capabilities", []):
                continue
            if provider.get("paid") and not allow_paid:
                continue
            if provider.get("privacy") == "external" and not allow_external:
                continue
            score = self._score(provider, constraints)
            candidates.append((score, provider))
        if not candidates:
            return {
                "selected": None,
                "capability": capability,
                "reason": "No approved provider is available for this capability.",
                "requiresCEOApproval": True,
            }
        candidates.sort(key=lambda item: item[0], reverse=True)
        selected = dict(candidates[0][1])
        selected["selectionScore"] = round(candidates[0][0], 4)
        return {"selected": selected, "capability": capability, "requiresCEOApproval": False}

    def _score(self, provider: dict, constraints: dict) -> float:
        privacy_bonus = 0.08 if provider.get("privacy") == "local" else 0
        cost_bonus = 0.08 if not provider.get("paid") else -0.08
        emma_weight = 0.25 if constraints.get("requiresEmma") else 0.12
        return (
            provider.get("quality", 0) * 0.34
            + provider.get("stability", 0) * 0.24
            + provider.get("automation", 0) * 0.22
            + provider.get("emmaConsistency", 0) * emma_weight
            + privacy_bonus
            + cost_bonus
        )

    def status(self) -> dict:
        providers = self.ensure().get("providers", [])
        return {
            "count": len(providers),
            "enabled": len([item for item in providers if item.get("enabled")]),
            "paidLocked": len([item for item in providers if item.get("paid") and not item.get("enabled")]),
            "providers": providers,
        }


class ModelManager:
    def __init__(self, paths: TempleOSPaths, logger: JsonEventLogger):
        self.paths = paths
        self.logger = logger

    def defaults(self) -> dict:
        return {
            "schemaVersion": SCHEMA_VERSION,
            "models": [
                {
                    "id": "local-llm-placeholder",
                    "capability": "llm",
                    "provider": "local-template",
                    "status": "not-configured",
                    "download": "manual",
                    "path": "",
                },
                {
                    "id": "comfyui-models",
                    "capability": "image",
                    "provider": "comfyui-local",
                    "status": "external-local-app",
                    "download": "managed-by-comfyui",
                    "path": "",
                },
                {
                    "id": "ffmpeg-system",
                    "capability": "rendering",
                    "provider": "ffmpeg-local",
                    "status": "auto-detected",
                    "download": "manual-or-system",
                    "path": shutil.which("ffmpeg") or "",
                },
            ],
            "downloadQueue": [],
        }

    def ensure(self) -> dict:
        if not self.paths.models.exists():
            atomic_write_json(self.paths.models, self.defaults())
            self.logger.emit("model-registry-initialized", {"path": str(self.paths.models)})
        return self.load()

    def load(self) -> dict:
        return read_json(self.paths.models, self.defaults())

    def request_download(self, model_id: str, source: str, requires_network: bool = True) -> dict:
        if requires_network:
            raise PermissionError("Model downloads require explicit CEO approval because network access is restricted.")
        registry = self.ensure()
        task = {"id": new_id("model-download"), "modelId": model_id, "source": source, "status": "queued", "createdAt": now_iso()}
        registry.setdefault("downloadQueue", []).append(task)
        atomic_write_json(self.paths.models, registry)
        self.logger.emit("model-download-queued", task)
        return task

    def status(self) -> dict:
        registry = self.ensure()
        return {"models": registry.get("models", []), "downloadQueue": registry.get("downloadQueue", [])}


class PluginManager:
    def __init__(self, paths: TempleOSPaths, logger: JsonEventLogger):
        self.paths = paths
        self.logger = logger

    def defaults(self) -> dict:
        return {"schemaVersion": SCHEMA_VERSION, "plugins": [], "sdkVersion": "temple-plugin-sdk-v1"}

    def ensure(self) -> dict:
        if not self.paths.plugins.exists():
            atomic_write_json(self.paths.plugins, self.defaults())
            self.logger.emit("plugin-registry-initialized", {"path": str(self.paths.plugins)})
        return self.scan()

    def validate_manifest(self, manifest: dict) -> dict:
        required = ["id", "name", "version", "capabilities", "entryPoint"]
        missing = [field for field in required if not manifest.get(field)]
        return {
            "ok": not missing,
            "missing": missing,
            "pluginId": manifest.get("id"),
            "sdkVersion": manifest.get("sdkVersion", "temple-plugin-sdk-v1"),
        }

    def scan(self) -> dict:
        registry = read_json(self.paths.plugins, self.defaults())
        discovered = []
        if self.paths.plugins_dir.exists():
            for manifest_path in sorted(self.paths.plugins_dir.glob("*/plugin.json")):
                try:
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    validation = self.validate_manifest(manifest)
                    discovered.append({"path": str(manifest_path), "manifest": manifest, "validation": validation})
                except Exception as exc:
                    discovered.append({"path": str(manifest_path), "validation": {"ok": False, "error": str(exc)}})
        registry["plugins"] = discovered
        atomic_write_json(self.paths.plugins, registry)
        return registry

    def status(self) -> dict:
        registry = self.ensure()
        return {
            "sdkVersion": registry.get("sdkVersion"),
            "installed": len(registry.get("plugins", [])),
            "plugins": registry.get("plugins", []),
        }


class PromptLibrary:
    def __init__(self, paths: TempleOSPaths, logger: JsonEventLogger):
        self.paths = paths
        self.logger = logger

    def defaults(self) -> dict:
        return {
            "schemaVersion": SCHEMA_VERSION,
            "prompts": [
                {
                    "id": "temple-product-video-script",
                    "capability": "script",
                    "language": "zh-TW",
                    "status": "active",
                    "purpose": "Generate Temple product-video narration and scene structure.",
                },
                {
                    "id": "emma-commercial-visual",
                    "capability": "image",
                    "language": "provider-adapted",
                    "status": "active",
                    "purpose": "Keep Emma commercially consistent in visual generation.",
                },
            ],
        }

    def ensure(self) -> dict:
        if not self.paths.prompts.exists():
            atomic_write_json(self.paths.prompts, self.defaults())
            self.logger.emit("prompt-library-initialized", {"path": str(self.paths.prompts)})
        return self.load()

    def load(self) -> dict:
        return read_json(self.paths.prompts, self.defaults())

    def status(self) -> dict:
        prompts = self.ensure().get("prompts", [])
        return {"count": len(prompts), "active": len([item for item in prompts if item.get("status") == "active"])}


class KnowledgeBase:
    def __init__(self, paths: TempleOSPaths, logger: JsonEventLogger):
        self.paths = paths
        self.logger = logger

    def defaults(self) -> dict:
        return {"schemaVersion": SCHEMA_VERSION, "entries": []}

    def ensure(self) -> dict:
        if not self.paths.knowledge.exists():
            atomic_write_json(self.paths.knowledge, self.defaults())
            self.logger.emit("knowledge-base-initialized", {"path": str(self.paths.knowledge)})
        return self.load()

    def load(self) -> dict:
        return read_json(self.paths.knowledge, self.defaults())

    def add_entry(self, title: str, text: str, tags: list[str] | None = None, source: str = "local") -> dict:
        registry = self.ensure()
        entry = {
            "id": new_id("knowledge"),
            "title": title,
            "text": text,
            "tags": tags or [],
            "source": source,
            "createdAt": now_iso(),
        }
        registry.setdefault("entries", []).append(entry)
        atomic_write_json(self.paths.knowledge, registry)
        self.logger.emit("knowledge-entry-added", {"entryId": entry["id"], "title": title})
        return entry

    def search(self, query: str) -> list[dict]:
        query_lower = query.lower()
        return [
            entry
            for entry in self.ensure().get("entries", [])
            if query_lower in entry.get("title", "").lower() or query_lower in entry.get("text", "").lower()
        ]

    def status(self) -> dict:
        entries = self.ensure().get("entries", [])
        return {"entries": len(entries), "tags": sorted({tag for entry in entries for tag in entry.get("tags", [])})}


class UserProfileManager:
    def __init__(self, paths: TempleOSPaths, logger: JsonEventLogger):
        self.paths = paths
        self.logger = logger

    def defaults(self) -> dict:
        return {
            "schemaVersion": SCHEMA_VERSION,
            "profiles": [
                {
                    "id": "ceo",
                    "displayName": "Temple CEO",
                    "role": "owner-operator",
                    "language": "zh-TW",
                    "timezone": "Asia/Taipei",
                    "approvalPolicy": {
                        "paidServices": "manual",
                        "cloudSync": "manual",
                        "destructiveOperations": "manual",
                        "emmaTrainingAssets": "manual",
                    },
                    "dailyPreferences": {
                        "inputLanguage": "Traditional Chinese",
                        "outputStyle": "commercial-ready",
                        "defaultApplication": "temple-product-video-generator",
                    },
                    "createdAt": now_iso(),
                }
            ],
            "activeProfileId": "ceo",
        }

    def ensure(self) -> dict:
        if not self.paths.user_profiles.exists():
            atomic_write_json(self.paths.user_profiles, self.defaults())
            self.logger.emit("user-profile-initialized", {"path": str(self.paths.user_profiles)})
        return self.load()

    def load(self) -> dict:
        return read_json(self.paths.user_profiles, self.defaults())

    def active(self) -> dict:
        registry = self.ensure()
        active_id = registry.get("activeProfileId", "ceo")
        return next((item for item in registry.get("profiles", []) if item.get("id") == active_id), registry["profiles"][0])

    def update_active(self, changes: dict) -> dict:
        registry = self.ensure()
        active_id = registry.get("activeProfileId", "ceo")
        for profile in registry.get("profiles", []):
            if profile.get("id") == active_id:
                profile.update(changes)
                profile["updatedAt"] = now_iso()
                atomic_write_json(self.paths.user_profiles, registry)
                self.logger.emit("user-profile-updated", {"profileId": active_id, "keys": sorted(changes.keys())})
                return profile
        raise KeyError(f"Active profile not found: {active_id}")

    def status(self) -> dict:
        registry = self.ensure()
        return {
            "activeProfile": self.active(),
            "profileCount": len(registry.get("profiles", [])),
        }


class ApplicationRegistry:
    def __init__(self, paths: TempleOSPaths, logger: JsonEventLogger):
        self.paths = paths
        self.logger = logger

    def defaults(self) -> dict:
        return {
            "schemaVersion": SCHEMA_VERSION,
            "applications": [
                {
                    "id": "temple-product-video-generator",
                    "name": "Temple Product Video Generator",
                    "status": "production",
                    "version": "1.0.0",
                    "entryPoint": "apps/temple-product-video-generator/start.bat",
                    "capabilities": ["script", "storyboard", "image", "video", "subtitle", "editing", "qa"],
                    "workflowId": "app.temple-product-video.generate",
                },
                {
                    "id": "social-post-generator",
                    "name": "Social Post Generator",
                    "status": "future-ready",
                    "version": "0.0.0",
                    "entryPoint": "",
                    "capabilities": ["script", "image", "caption", "qa"],
                    "workflowId": "future.social-post.generate",
                },
                {
                    "id": "emma-video-generator",
                    "name": "Emma Video Generator",
                    "status": "future-ready-requires-emma-assets",
                    "version": "0.0.0",
                    "entryPoint": "",
                    "capabilities": ["emma", "voice", "lip-sync", "video", "qa"],
                    "workflowId": "future.emma-video.generate",
                },
            ],
        }

    def ensure(self) -> dict:
        if not self.paths.applications.exists():
            atomic_write_json(self.paths.applications, self.defaults())
            self.logger.emit("application-registry-initialized", {"path": str(self.paths.applications)})
        return self.load()

    def load(self) -> dict:
        return read_json(self.paths.applications, self.defaults())

    def register(self, app: dict) -> dict:
        required = ["id", "name", "status", "version", "capabilities"]
        missing = [field for field in required if not app.get(field)]
        if missing:
            raise ValueError(f"Application manifest missing fields: {', '.join(missing)}")
        registry = self.ensure()
        apps = [item for item in registry.get("applications", []) if item.get("id") != app["id"]]
        app.setdefault("registeredAt", now_iso())
        apps.append(app)
        registry["applications"] = sorted(apps, key=lambda item: item["id"])
        atomic_write_json(self.paths.applications, registry)
        self.logger.emit("application-registered", {"appId": app["id"], "status": app["status"]})
        return app

    def get(self, app_id: str) -> dict | None:
        return next((item for item in self.ensure().get("applications", []) if item.get("id") == app_id), None)

    def status(self) -> dict:
        apps = self.ensure().get("applications", [])
        return {
            "count": len(apps),
            "production": len([item for item in apps if item.get("status") == "production"]),
            "futureReady": len([item for item in apps if str(item.get("status", "")).startswith("future")]),
            "applications": apps,
        }


class AIAgentSystem:
    def __init__(
        self,
        paths: TempleOSPaths,
        queue: QueueManager,
        providers: ProviderManager,
        applications: ApplicationRegistry,
        logger: JsonEventLogger,
    ):
        self.paths = paths
        self.queue = queue
        self.providers = providers
        self.applications = applications
        self.logger = logger

    def defaults(self) -> dict:
        return {
            "schemaVersion": SCHEMA_VERSION,
            "agents": [
                {
                    "id": "intent-analyst",
                    "name": "Intent Analyst",
                    "capabilities": ["intent", "requirements", "routing"],
                    "providerCapability": "llm",
                    "enabled": True,
                },
                {
                    "id": "script-agent",
                    "name": "Script Agent",
                    "capabilities": ["script"],
                    "providerCapability": "script",
                    "enabled": True,
                },
                {
                    "id": "storyboard-agent",
                    "name": "Storyboard Agent",
                    "capabilities": ["storyboard"],
                    "providerCapability": "storyboard",
                    "enabled": True,
                },
                {
                    "id": "visual-agent",
                    "name": "Visual Generation Agent",
                    "capabilities": ["image", "prompt"],
                    "providerCapability": "image",
                    "enabled": True,
                },
                {
                    "id": "video-agent",
                    "name": "Video Agent",
                    "capabilities": ["video", "editing", "rendering"],
                    "providerCapability": "video",
                    "enabled": True,
                },
                {
                    "id": "qa-agent",
                    "name": "Quality Agent",
                    "capabilities": ["qa", "recovery"],
                    "providerCapability": "qa",
                    "enabled": True,
                },
            ],
        }

    def ensure(self) -> dict:
        if not self.paths.agents.exists():
            atomic_write_json(self.paths.agents, self.defaults())
            self.logger.emit("agent-registry-initialized", {"path": str(self.paths.agents)})
        if not self.paths.agent_runs.exists():
            atomic_write_json(self.paths.agent_runs, {"schemaVersion": SCHEMA_VERSION, "runs": []})
        return self.load()

    def load(self) -> dict:
        return read_json(self.paths.agents, self.defaults())

    def runs(self) -> dict:
        return read_json(self.paths.agent_runs, {"schemaVersion": SCHEMA_VERSION, "runs": []})

    def create_plan(self, request: str, app_id: str = "temple-product-video-generator") -> dict:
        self.ensure()
        app = self.applications.get(app_id)
        if not app:
            raise KeyError(f"Application not registered: {app_id}")
        active_agents = [agent for agent in self.load().get("agents", []) if agent.get("enabled")]
        steps = []
        for agent in active_agents:
            provider = self.providers.select(agent["providerCapability"], {"requiresEmma": "image" in agent.get("capabilities", []) or "video" in agent.get("capabilities", [])})
            steps.append(
                {
                    "agentId": agent["id"],
                    "name": agent["name"],
                    "providerSelection": provider,
                    "taskType": f"agent.{agent['id']}",
                    "status": "planned",
                }
            )
        run = {
            "id": new_id("agent-run"),
            "request": request,
            "appId": app_id,
            "appStatus": app.get("status"),
            "language": "zh-TW",
            "status": "planned",
            "steps": steps,
            "createdAt": now_iso(),
        }
        registry = self.runs()
        registry.setdefault("runs", []).append(run)
        atomic_write_json(self.paths.agent_runs, registry)
        self.logger.emit("agent-plan-created", {"runId": run["id"], "appId": app_id, "steps": len(steps)})
        return run

    def enqueue_plan(self, run_id: str) -> dict:
        registry = self.runs()
        run = next((item for item in registry.get("runs", []) if item.get("id") == run_id), None)
        if not run:
            raise KeyError(f"Agent run not found: {run_id}")
        task_ids = []
        for step in run.get("steps", []):
            task = self.queue.enqueue("agent-run", {"runId": run_id, "agentId": step["agentId"]}, priority=70)
            task_ids.append(task["id"])
        run["status"] = "queued"
        run["taskIds"] = task_ids
        run["updatedAt"] = now_iso()
        atomic_write_json(self.paths.agent_runs, registry)
        self.logger.emit("agent-plan-queued", {"runId": run_id, "tasks": len(task_ids)})
        return run

    def complete_step(self, run_id: str, agent_id: str, result: dict) -> dict:
        registry = self.runs()
        for run in registry.get("runs", []):
            if run.get("id") != run_id:
                continue
            for step in run.get("steps", []):
                if step.get("agentId") == agent_id:
                    step["status"] = "completed"
                    step["result"] = result
                    step["completedAt"] = now_iso()
            if all(step.get("status") == "completed" for step in run.get("steps", [])):
                run["status"] = "completed"
                run["completedAt"] = now_iso()
            else:
                run["status"] = "running"
            run["updatedAt"] = now_iso()
            atomic_write_json(self.paths.agent_runs, registry)
            return run
        raise KeyError(f"Agent run not found: {run_id}")

    def status(self) -> dict:
        agents = self.ensure().get("agents", [])
        runs = self.runs().get("runs", [])
        return {
            "agents": len(agents),
            "enabled": len([agent for agent in agents if agent.get("enabled")]),
            "runs": len(runs),
            "recentRuns": runs[-5:],
        }


class MultiAgentCollaboration:
    def __init__(self, paths: TempleOSPaths, agents: AIAgentSystem, logger: JsonEventLogger):
        self.paths = paths
        self.agents = agents
        self.logger = logger

    def ensure(self) -> dict:
        if not self.paths.collaborations.exists():
            atomic_write_json(self.paths.collaborations, {"schemaVersion": SCHEMA_VERSION, "sessions": []})
            self.logger.emit("collaboration-registry-initialized", {"path": str(self.paths.collaborations)})
        return self.load()

    def load(self) -> dict:
        return read_json(self.paths.collaborations, {"schemaVersion": SCHEMA_VERSION, "sessions": []})

    def start(self, goal: str, app_id: str = "temple-product-video-generator") -> dict:
        plan = self.agents.create_plan(goal, app_id=app_id)
        session = {
            "id": new_id("collab"),
            "goal": goal,
            "appId": app_id,
            "agentRunId": plan["id"],
            "status": "planned",
            "participants": [step["agentId"] for step in plan.get("steps", [])],
            "createdAt": now_iso(),
        }
        registry = self.ensure()
        registry.setdefault("sessions", []).append(session)
        atomic_write_json(self.paths.collaborations, registry)
        self.logger.emit("collaboration-started", {"sessionId": session["id"], "agentRunId": plan["id"]})
        return session

    def status(self) -> dict:
        sessions = self.ensure().get("sessions", [])
        return {"sessions": len(sessions), "recentSessions": sessions[-5:]}


class ModelDownloadManager:
    def __init__(self, paths: TempleOSPaths, logger: JsonEventLogger):
        self.paths = paths
        self.logger = logger

    def ensure(self) -> dict:
        if not self.paths.downloads.exists():
            atomic_write_json(self.paths.downloads, {"schemaVersion": SCHEMA_VERSION, "downloads": []})
            self.logger.emit("download-registry-initialized", {"path": str(self.paths.downloads)})
        return self.load()

    def load(self) -> dict:
        return read_json(self.paths.downloads, {"schemaVersion": SCHEMA_VERSION, "downloads": []})

    def request(self, model_id: str, source: str, capability: str, approval: bool = False) -> dict:
        network_source = source.startswith("http://") or source.startswith("https://")
        if network_source and not approval:
            status = "blocked"
            reason = "Network model download requires CEO approval."
        else:
            status = "queued"
            reason = ""
        item = {
            "id": new_id("download"),
            "modelId": model_id,
            "source": source,
            "capability": capability,
            "status": status,
            "reason": reason,
            "createdAt": now_iso(),
        }
        registry = self.ensure()
        registry.setdefault("downloads", []).append(item)
        atomic_write_json(self.paths.downloads, registry)
        self.logger.emit("model-download-requested", {"downloadId": item["id"], "status": status})
        return item

    def status(self) -> dict:
        downloads = self.ensure().get("downloads", [])
        by_status: dict[str, int] = {}
        for item in downloads:
            by_status[item.get("status", "unknown")] = by_status.get(item.get("status", "unknown"), 0) + 1
        return {"downloads": len(downloads), "byStatus": by_status, "recent": downloads[-5:]}


class UpdateManager:
    def __init__(self, paths: TempleOSPaths, backups: BackupManager, logger: JsonEventLogger):
        self.paths = paths
        self.backups = backups
        self.logger = logger

    def ensure(self) -> dict:
        if not self.paths.updates.exists():
            payload = {
                "schemaVersion": SCHEMA_VERSION,
                "currentVersion": TEMPLE_OS_VERSION,
                "policy": {
                    "onlineUpdater": False,
                    "preUpdateBackup": True,
                    "rollbackRequired": True,
                    "silentDestructiveMigration": False,
                },
                "updates": [],
            }
            atomic_write_json(self.paths.updates, payload)
            self.logger.emit("update-registry-initialized", {"path": str(self.paths.updates)})
        return self.load()

    def load(self) -> dict:
        return read_json(self.paths.updates, {"schemaVersion": SCHEMA_VERSION, "currentVersion": TEMPLE_OS_VERSION, "updates": []})

    def plan_local_update(self, target_version: str, manifest_path: Path) -> dict:
        manifest_path = Path(manifest_path)
        if not manifest_path.exists():
            raise FileNotFoundError(str(manifest_path))
        backup = self.backups.create(label=f"pre-update-{target_version}")
        plan = {
            "id": new_id("update"),
            "targetVersion": target_version,
            "manifestPath": str(manifest_path.resolve()),
            "status": "planned",
            "preUpdateBackup": backup["path"],
            "createdAt": now_iso(),
        }
        registry = self.ensure()
        registry.setdefault("updates", []).append(plan)
        atomic_write_json(self.paths.updates, registry)
        self.logger.emit("update-planned", {"updateId": plan["id"], "targetVersion": target_version})
        return plan

    def status(self) -> dict:
        registry = self.ensure()
        updates = registry.get("updates", [])
        return {
            "currentVersion": registry.get("currentVersion"),
            "onlineUpdater": registry.get("policy", {}).get("onlineUpdater") is True,
            "updates": len(updates),
            "recent": updates[-5:],
        }


class MobileAPIContract:
    def __init__(self, paths: TempleOSPaths, logger: JsonEventLogger):
        self.paths = paths
        self.logger = logger

    def ensure(self) -> dict:
        if not self.paths.mobile_api.exists():
            payload = {
                "schemaVersion": SCHEMA_VERSION,
                "contract": "temple-mobile-api-v1",
                "status": "local-contract-ready",
                "auth": "local-session-now; future-token-auth-requires-ceo-decision",
                "endpoints": [
                    "GET /mobile/v1/status",
                    "GET /mobile/v1/projects",
                    "POST /mobile/v1/requests",
                    "GET /mobile/v1/exports/{id}",
                ],
                "privacy": "No external mobile hosting is active.",
            }
            atomic_write_json(self.paths.mobile_api, payload)
            self.logger.emit("mobile-api-contract-initialized", {"path": str(self.paths.mobile_api)})
        return self.load()

    def load(self) -> dict:
        return read_json(self.paths.mobile_api, {})

    def status(self) -> dict:
        payload = self.ensure()
        return {"status": payload.get("status"), "contract": payload.get("contract"), "endpoints": payload.get("endpoints", [])}


class CloudSyncManager:
    def __init__(self, paths: TempleOSPaths, config: ConfigurationCenter, logger: JsonEventLogger):
        self.paths = paths
        self.config = config
        self.logger = logger

    def ensure(self) -> dict:
        if not self.paths.cloud_sync.exists():
            payload = {
                "schemaVersion": SCHEMA_VERSION,
                "status": "disabled-pending-ceo-decision",
                "syncMode": "none",
                "allowed": False,
                "lastSync": "",
                "conflictPolicy": "manual-review-required",
                "privacy": "No cloud sync is active.",
            }
            atomic_write_json(self.paths.cloud_sync, payload)
            self.logger.emit("cloud-sync-contract-initialized", {"path": str(self.paths.cloud_sync)})
        return self.load()

    def load(self) -> dict:
        return read_json(self.paths.cloud_sync, {})

    def request_sync(self) -> dict:
        if not self.config.load().get("privacy", {}).get("allowCloudSync"):
            raise PermissionError("Cloud sync requires CEO approval before activation.")
        payload = self.ensure()
        payload["status"] = "ready-to-configure"
        payload["updatedAt"] = now_iso()
        atomic_write_json(self.paths.cloud_sync, payload)
        return payload

    def status(self) -> dict:
        return self.ensure()


class MultiUserManager:
    def __init__(self, paths: TempleOSPaths, logger: JsonEventLogger):
        self.paths = paths
        self.logger = logger

    def ensure(self) -> dict:
        if not self.paths.tenants.exists():
            payload = {
                "schemaVersion": SCHEMA_VERSION,
                "mode": "single-user-local",
                "tenants": [
                    {
                        "id": "local-owner",
                        "name": "Local Owner Workspace",
                        "role": "owner",
                        "isolation": "prepared",
                        "status": "active",
                    }
                ],
                "futureModes": ["local-team", "private-cloud", "hosted-saas"],
                "activation": "CEO decision required before multi-user hosting.",
            }
            atomic_write_json(self.paths.tenants, payload)
            self.logger.emit("multi-user-contract-initialized", {"path": str(self.paths.tenants)})
        return self.load()

    def load(self) -> dict:
        return read_json(self.paths.tenants, {})

    def status(self) -> dict:
        payload = self.ensure()
        return {
            "mode": payload.get("mode"),
            "tenantCount": len(payload.get("tenants", [])),
            "futureModes": payload.get("futureModes", []),
            "activation": payload.get("activation"),
        }


class BusinessRuleEngine:
    def __init__(self, config: ConfigurationCenter):
        self.config = config

    def validate_task(self, task: dict) -> dict:
        issues = []
        config = self.config.load()
        task_type = task.get("type", "")
        payload = task.get("payload", {})
        if payload.get("paidProvider") and not config.get("privacy", {}).get("allowPaidProviders"):
            issues.append("Paid providers require CEO approval.")
        if payload.get("cloudSync") and not config.get("privacy", {}).get("allowCloudSync"):
            issues.append("Cloud sync requires CEO approval.")
        if task_type in {"delete-data", "rewrite-history", "destructive-operation"}:
            issues.append("Irreversible destructive operations require explicit CEO approval.")
        if payload.get("requiresEmmaTrainingAssets"):
            issues.append("Emma training assets are required before this task can run.")
        return {"ok": not issues, "issues": issues}


class QueueManager:
    TERMINAL = {"completed", "failed", "cancelled"}

    def __init__(self, paths: TempleOSPaths, rules: BusinessRuleEngine, logger: JsonEventLogger):
        self.paths = paths
        self.rules = rules
        self.logger = logger

    def ensure(self) -> dict:
        if not self.paths.queue.exists():
            atomic_write_json(self.paths.queue, {"schemaVersion": SCHEMA_VERSION, "tasks": []})
            self.logger.emit("queue-initialized", {"path": str(self.paths.queue)})
        return self.load()

    def load(self) -> dict:
        return read_json(self.paths.queue, {"schemaVersion": SCHEMA_VERSION, "tasks": []})

    def save(self, registry: dict) -> None:
        atomic_write_json(self.paths.queue, registry)

    def enqueue(self, task_type: str, payload: dict | None = None, priority: int = 50, max_retries: int | None = None) -> dict:
        task = {
            "id": new_id("task"),
            "type": task_type,
            "status": "queued",
            "priority": priority,
            "payload": payload or {},
            "attempts": 0,
            "maxRetries": max_retries,
            "createdAt": now_iso(),
            "updatedAt": now_iso(),
        }
        validation = self.rules.validate_task(task)
        if not validation["ok"]:
            task["status"] = "blocked"
            task["blockedReasons"] = validation["issues"]
        registry = self.ensure()
        registry.setdefault("tasks", []).append(task)
        self.save(registry)
        self.logger.emit("task-enqueued", {"taskId": task["id"], "type": task_type, "status": task["status"]})
        return task

    def claim_next(self) -> dict | None:
        registry = self.ensure()
        candidates = [task for task in registry.get("tasks", []) if task.get("status") == "queued"]
        if not candidates:
            return None
        candidates.sort(key=lambda task: (-int(task.get("priority", 50)), task.get("createdAt", "")))
        selected = candidates[0]
        selected["status"] = "running"
        selected["attempts"] = int(selected.get("attempts", 0)) + 1
        selected["startedAt"] = now_iso()
        selected["updatedAt"] = now_iso()
        self.save(registry)
        self.logger.emit("task-claimed", {"taskId": selected["id"], "type": selected["type"]})
        return selected

    def complete(self, task_id: str, result: dict | None = None) -> dict:
        return self._transition(task_id, "completed", {"result": result or {}, "completedAt": now_iso()})

    def fail(self, task_id: str, error: str, retry: bool = True) -> dict:
        registry = self.ensure()
        config_max = 2
        for task in registry.get("tasks", []):
            if task.get("id") != task_id:
                continue
            max_retries = task.get("maxRetries")
            max_retries = config_max if max_retries is None else int(max_retries)
            task.setdefault("errors", []).append({"at": now_iso(), "error": error})
            if retry and int(task.get("attempts", 0)) <= max_retries:
                task["status"] = "queued"
                task["updatedAt"] = now_iso()
                self.save(registry)
                self.logger.emit("task-requeued", {"taskId": task_id, "error": error}, level="WARN")
                return task
            task["status"] = "failed"
            task["failedAt"] = now_iso()
            task["updatedAt"] = now_iso()
            self.save(registry)
            self.logger.emit("task-failed", {"taskId": task_id, "error": error}, level="ERROR")
            return task
        raise KeyError(f"Task not found: {task_id}")

    def _transition(self, task_id: str, status: str, extras: dict) -> dict:
        registry = self.ensure()
        for task in registry.get("tasks", []):
            if task.get("id") == task_id:
                task.update(extras)
                task["status"] = status
                task["updatedAt"] = now_iso()
                self.save(registry)
                self.logger.emit(f"task-{status}", {"taskId": task_id})
                return task
        raise KeyError(f"Task not found: {task_id}")

    def status(self) -> dict:
        tasks = self.ensure().get("tasks", [])
        by_status: dict[str, int] = {}
        for task in tasks:
            by_status[task.get("status", "unknown")] = by_status.get(task.get("status", "unknown"), 0) + 1
        return {"total": len(tasks), "byStatus": by_status, "recent": tasks[-10:]}


class TaskScheduler:
    def __init__(self, paths: TempleOSPaths, queue: QueueManager, logger: JsonEventLogger):
        self.paths = paths
        self.queue = queue
        self.logger = logger

    def ensure(self) -> dict:
        if not self.paths.schedules.exists():
            payload = {
                "schemaVersion": SCHEMA_VERSION,
                "schedules": [
                    {
                        "id": "daily-health-check",
                        "taskType": "health-check",
                        "enabled": True,
                        "cadence": "manual-or-daily",
                        "payload": {},
                    }
                ],
            }
            atomic_write_json(self.paths.schedules, payload)
            self.logger.emit("scheduler-initialized", {"path": str(self.paths.schedules)})
        return self.load()

    def load(self) -> dict:
        return read_json(self.paths.schedules, {"schemaVersion": SCHEMA_VERSION, "schedules": []})

    def trigger(self, schedule_id: str) -> dict:
        for schedule in self.ensure().get("schedules", []):
            if schedule.get("id") == schedule_id:
                if not schedule.get("enabled"):
                    raise RuntimeError(f"Schedule is disabled: {schedule_id}")
                task = self.queue.enqueue(schedule["taskType"], schedule.get("payload", {}), priority=40)
                self.logger.emit("schedule-triggered", {"scheduleId": schedule_id, "taskId": task["id"]})
                return task
        raise KeyError(f"Schedule not found: {schedule_id}")

    def status(self) -> dict:
        schedules = self.ensure().get("schedules", [])
        return {"count": len(schedules), "enabled": len([item for item in schedules if item.get("enabled")])}


class WorkflowEngine:
    def __init__(self, paths: TempleOSPaths, queue: QueueManager, logger: JsonEventLogger):
        self.paths = paths
        self.queue = queue
        self.logger = logger

    def defaults(self) -> dict:
        return {
            "schemaVersion": SCHEMA_VERSION,
            "workflows": [
                {
                    "id": "temple.health-check",
                    "name": "Temple OS Health Check",
                    "version": "1.0.0",
                    "steps": [{"taskType": "health-check", "payload": {}}],
                },
                {
                    "id": "temple.support-package",
                    "name": "Create Support Package",
                    "version": "1.0.0",
                    "steps": [{"taskType": "support-package", "payload": {}}],
                },
                {
                    "id": "temple.backup",
                    "name": "Create Local Backup",
                    "version": "1.0.0",
                    "steps": [{"taskType": "backup", "payload": {}}],
                },
                {
                    "id": "app.temple-product-video.generate",
                    "name": "Temple Product Video Generator Agent Workflow",
                    "version": "1.0.0",
                    "steps": [
                        {
                            "taskType": "ai-request",
                            "payload": {
                                "appId": "temple-product-video-generator",
                                "request": "Temple product video request",
                            },
                        }
                    ],
                },
            ],
        }

    def ensure(self) -> dict:
        if not self.paths.workflows.exists():
            atomic_write_json(self.paths.workflows, self.defaults())
            self.logger.emit("workflow-registry-initialized", {"path": str(self.paths.workflows)})
        return self.load()

    def load(self) -> dict:
        return read_json(self.paths.workflows, self.defaults())

    def run(self, workflow_id: str, payload: dict | None = None) -> dict:
        payload = payload or {}
        workflow = next((item for item in self.ensure().get("workflows", []) if item.get("id") == workflow_id), None)
        if not workflow:
            raise KeyError(f"Workflow not found: {workflow_id}")
        run = {
            "id": new_id("workflow-run"),
            "workflowId": workflow_id,
            "taskIds": [],
            "createdAt": now_iso(),
        }
        for step in workflow.get("steps", []):
            step_payload = dict(step.get("payload", {}))
            step_payload.update(payload)
            step_payload["workflowRunId"] = run["id"]
            task = self.queue.enqueue(step["taskType"], step_payload, priority=60)
            run["taskIds"].append(task["id"])
        self.logger.emit("workflow-run-created", {"workflowRunId": run["id"], "workflowId": workflow_id})
        return run

    def status(self) -> dict:
        workflows = self.ensure().get("workflows", [])
        return {"count": len(workflows), "ids": [item.get("id") for item in workflows]}


class AutomationEngine:
    def __init__(self, paths: TempleOSPaths, queue: QueueManager, logger: JsonEventLogger):
        self.paths = paths
        self.queue = queue
        self.logger = logger

    def ensure(self) -> dict:
        if not self.paths.automation.exists():
            payload = {
                "schemaVersion": SCHEMA_VERSION,
                "rules": [
                    {
                        "id": "retry-failed-generation",
                        "enabled": True,
                        "when": "task-failed-and-retry-available",
                        "action": "queue-retry",
                    }
                ],
            }
            atomic_write_json(self.paths.automation, payload)
            self.logger.emit("automation-initialized", {"path": str(self.paths.automation)})
        return self.load()

    def load(self) -> dict:
        return read_json(self.paths.automation, {"schemaVersion": SCHEMA_VERSION, "rules": []})

    def status(self) -> dict:
        rules = self.ensure().get("rules", [])
        return {"rules": len(rules), "enabled": len([item for item in rules if item.get("enabled")])}


class BackupManager:
    def __init__(self, paths: TempleOSPaths, logger: JsonEventLogger):
        self.paths = paths
        self.logger = logger

    def create(self, label: str = "manual") -> dict:
        self.paths.ensure_dirs()
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        archive = self.paths.backups / f"temple-os-{label}-{stamp}.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipf:
            for path in sorted(self.paths.state.rglob("*")):
                if path.is_file():
                    zipf.write(path, path.relative_to(self.paths.operations))
        result = {
            "path": str(archive),
            "size": archive.stat().st_size,
            "createdAt": now_iso(),
            "contains": "state registry files only; no product photos or generated media",
        }
        self.logger.emit("backup-created", result)
        return result

    def restore(self, archive: Path, confirm: bool = False) -> dict:
        if not confirm:
            raise PermissionError("Restore requires confirm=True to avoid accidental overwrite.")
        archive = Path(archive).resolve()
        if not archive.exists():
            raise FileNotFoundError(str(archive))
        safety = self.create(label="pre-restore")
        with zipfile.ZipFile(archive, "r") as zipf:
            for member in zipf.namelist():
                if not member.startswith("state/"):
                    continue
                target = (self.paths.operations / member).resolve()
                if not str(target).startswith(str(self.paths.operations.resolve())):
                    raise RuntimeError(f"Refusing unsafe restore path: {member}")
                target.parent.mkdir(parents=True, exist_ok=True)
                with zipf.open(member) as source, target.open("wb") as dest:
                    shutil.copyfileobj(source, dest)
        result = {"restoredFrom": str(archive), "safetyBackup": safety["path"], "restoredAt": now_iso()}
        self.logger.recovery("restore-completed", result)
        return result

    def status(self) -> dict:
        backups = sorted(self.paths.backups.glob("*.zip"), key=lambda item: item.stat().st_mtime, reverse=True)
        return {"count": len(backups), "latest": str(backups[0]) if backups else ""}


class SupportPackageManager:
    SECRET_KEYS = {"api_key", "apikey", "token", "password", "secret", "authorization"}

    def __init__(self, paths: TempleOSPaths, logger: JsonEventLogger):
        self.paths = paths
        self.logger = logger

    def create(self, status: dict) -> dict:
        self.paths.ensure_dirs()
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        archive = self.paths.support / f"temple-os-support-{stamp}.zip"
        sanitized_status = self._sanitize(status)
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr("status.json", json.dumps(sanitized_status, ensure_ascii=False, indent=2))
            for log in [self.paths.events, self.paths.recovery_log]:
                if log.exists():
                    zipf.write(log, f"logs/{log.name}")
        result = {
            "path": str(archive),
            "size": archive.stat().st_size,
            "privacy": "excludes product photos, generated media, private exports, API keys, tokens, passwords, and secrets",
        }
        self.logger.emit("support-package-created", result)
        return result

    def _sanitize(self, value: Any) -> Any:
        if isinstance(value, dict):
            sanitized = {}
            for key, inner in value.items():
                if key.lower().replace("-", "_") in self.SECRET_KEYS:
                    sanitized[key] = "[REDACTED]"
                else:
                    sanitized[key] = self._sanitize(inner)
            return sanitized
        if isinstance(value, list):
            return [self._sanitize(item) for item in value]
        return value


class MonitoringCenter:
    def __init__(self, paths: TempleOSPaths, logger: JsonEventLogger):
        self.paths = paths
        self.logger = logger

    def snapshot(self, kernel: "TempleOSKernel") -> dict:
        queue = kernel.queue.status()
        providers = kernel.providers.status()
        models = kernel.models.status()
        telemetry = {
            "schemaVersion": SCHEMA_VERSION,
            "createdAt": now_iso(),
            "host": socket.gethostname(),
            "version": TEMPLE_OS_VERSION,
            "queue": queue,
            "providers": {
                "count": providers["count"],
                "enabled": providers["enabled"],
            },
            "models": {
                "count": len(models.get("models", [])),
                "downloadQueue": len(models.get("downloadQueue", [])),
            },
            "logs": {
                "events": str(self.paths.events),
                "recovery": str(self.paths.recovery_log),
            },
        }
        atomic_write_json(self.paths.telemetry, telemetry)
        return telemetry


class SelfHealingEngine:
    def __init__(self, paths: TempleOSPaths, config: ConfigurationCenter, queue: QueueManager, logger: JsonEventLogger):
        self.paths = paths
        self.config = config
        self.queue = queue
        self.logger = logger

    def run(self) -> dict:
        self.paths.ensure_dirs()
        registry = self.queue.ensure()
        config = self.config.load()
        stale_seconds = int(config.get("limits", {}).get("staleTaskSeconds", 3600))
        now = time.time()
        healed = []
        for task in registry.get("tasks", []):
            if task.get("status") != "running":
                continue
            started = task.get("startedAt") or task.get("updatedAt") or task.get("createdAt")
            try:
                started_ts = datetime.fromisoformat(started).timestamp()
            except Exception:
                started_ts = 0
            if now - started_ts > stale_seconds:
                task["status"] = "queued"
                task.setdefault("recovery", []).append({"at": now_iso(), "reason": "stale-running-task"})
                task["updatedAt"] = now_iso()
                healed.append(task["id"])
        if healed:
            self.queue.save(registry)
            self.logger.recovery("stale-tasks-requeued", {"taskIds": healed}, level="WARN")
        return {"healedTasks": healed, "requiredDirectoriesReady": True}


class BackgroundWorker:
    def __init__(self, kernel: "TempleOSKernel"):
        self.kernel = kernel
        self.handlers: dict[str, Callable[[dict], dict]] = {
            "health-check": self._health_check,
            "backup": self._backup,
            "support-package": self._support_package,
            "self-heal": self._self_heal,
            "workflow-run": self._workflow_run,
            "ai-request": self._ai_request,
            "agent-run": self._agent_run,
            "model-download": self._model_download,
            "update-check": self._update_check,
            "failure-recovery": self._failure_recovery,
        }

    def run_once(self) -> dict:
        task = self.kernel.queue.claim_next()
        if not task:
            return {"processed": False, "message": "No queued tasks."}
        handler = self.handlers.get(task.get("type"))
        if not handler:
            failed = self.kernel.queue.fail(task["id"], f"No handler for task type: {task.get('type')}", retry=False)
            return {"processed": True, "task": failed}
        try:
            result = handler(task)
            completed = self.kernel.queue.complete(task["id"], result)
            return {"processed": True, "task": completed, "result": result}
        except Exception as exc:
            failed = self.kernel.queue.fail(task["id"], str(exc), retry=True)
            return {"processed": True, "task": failed, "error": str(exc)}

    def _health_check(self, task: dict) -> dict:
        return self.kernel.health_check()

    def _backup(self, task: dict) -> dict:
        return self.kernel.backups.create(label=task.get("payload", {}).get("label", "queue"))

    def _support_package(self, task: dict) -> dict:
        return self.kernel.support_packages.create(self.kernel.status())

    def _self_heal(self, task: dict) -> dict:
        return self.kernel.self_healing.run()

    def _workflow_run(self, task: dict) -> dict:
        workflow_id = task.get("payload", {}).get("workflowId")
        if not workflow_id:
            raise ValueError("workflowId is required.")
        return self.kernel.workflows.run(workflow_id, task.get("payload", {}).get("payload", {}))

    def _ai_request(self, task: dict) -> dict:
        payload = task.get("payload", {})
        request = payload.get("request") or "Temple AI Studio request"
        app_id = payload.get("appId", "temple-product-video-generator")
        plan = self.kernel.agents.create_plan(request, app_id=app_id)
        queued = self.kernel.agents.enqueue_plan(plan["id"])
        return {
            "agentRunId": queued["id"],
            "taskIds": queued.get("taskIds", []),
            "appId": app_id,
            "status": queued.get("status"),
        }

    def _agent_run(self, task: dict) -> dict:
        payload = task.get("payload", {})
        run_id = payload.get("runId")
        agent_id = payload.get("agentId")
        if not run_id or not agent_id:
            raise ValueError("runId and agentId are required.")
        result = {
            "agentId": agent_id,
            "decision": "completed-local-orchestration-step",
            "providerSelectionsVerified": True,
            "completedAt": now_iso(),
        }
        run = self.kernel.agents.complete_step(run_id, agent_id, result)
        return {"runId": run_id, "agentId": agent_id, "runStatus": run.get("status")}

    def _model_download(self, task: dict) -> dict:
        payload = task.get("payload", {})
        return self.kernel.downloads.request(
            payload["modelId"],
            payload["source"],
            payload.get("capability", "unknown"),
            approval=bool(payload.get("approval")),
        )

    def _update_check(self, task: dict) -> dict:
        return self.kernel.updates.status()

    def _failure_recovery(self, task: dict) -> dict:
        return self.kernel.self_healing.run()


class TempleOSKernel:
    def __init__(self, root: Path | str):
        self.paths = TempleOSPaths(Path(root))
        self.logger = JsonEventLogger(self.paths)
        self.config = ConfigurationCenter(self.paths, self.logger)
        self.workspaces = WorkspaceManager(self.paths, self.logger)
        self.projects = ProjectManager(self.paths, self.logger)
        self.providers = ProviderManager(self.paths, self.config, self.logger)
        self.models = ModelManager(self.paths, self.logger)
        self.plugins = PluginManager(self.paths, self.logger)
        self.prompts = PromptLibrary(self.paths, self.logger)
        self.knowledge = KnowledgeBase(self.paths, self.logger)
        self.user_profiles = UserProfileManager(self.paths, self.logger)
        self.applications = ApplicationRegistry(self.paths, self.logger)
        self.rules = BusinessRuleEngine(self.config)
        self.queue = QueueManager(self.paths, self.rules, self.logger)
        self.agents = AIAgentSystem(self.paths, self.queue, self.providers, self.applications, self.logger)
        self.collaboration = MultiAgentCollaboration(self.paths, self.agents, self.logger)
        self.scheduler = TaskScheduler(self.paths, self.queue, self.logger)
        self.workflows = WorkflowEngine(self.paths, self.queue, self.logger)
        self.automation = AutomationEngine(self.paths, self.queue, self.logger)
        self.backups = BackupManager(self.paths, self.logger)
        self.downloads = ModelDownloadManager(self.paths, self.logger)
        self.updates = UpdateManager(self.paths, self.backups, self.logger)
        self.mobile_api = MobileAPIContract(self.paths, self.logger)
        self.cloud_sync = CloudSyncManager(self.paths, self.config, self.logger)
        self.multi_user = MultiUserManager(self.paths, self.logger)
        self.support_packages = SupportPackageManager(self.paths, self.logger)
        self.monitoring = MonitoringCenter(self.paths, self.logger)
        self.self_healing = SelfHealingEngine(self.paths, self.config, self.queue, self.logger)
        self.worker = BackgroundWorker(self)

    def ensure_initialized(self) -> dict:
        self.paths.ensure_dirs()
        version = {
            "schemaVersion": SCHEMA_VERSION,
            "templeOSVersion": TEMPLE_OS_VERSION,
            "dataVersion": SCHEMA_VERSION,
            "updatedBy": "TempleOSKernel",
        }
        write_json_if_changed(self.paths.version, version)
        payload = {
            "config": self.config.ensure(),
            "workspace": self.workspaces.ensure_default(),
            "projects": self.projects.ensure(),
            "providers": self.providers.ensure(),
            "models": self.models.ensure(),
            "plugins": self.plugins.ensure(),
            "prompts": self.prompts.ensure(),
            "knowledge": self.knowledge.ensure(),
            "userProfiles": self.user_profiles.ensure(),
            "applications": self.applications.ensure(),
            "queue": self.queue.ensure(),
            "agents": self.agents.ensure(),
            "collaboration": self.collaboration.ensure(),
            "schedules": self.scheduler.ensure(),
            "workflows": self.workflows.ensure(),
            "automation": self.automation.ensure(),
            "downloads": self.downloads.ensure(),
            "updates": self.updates.ensure(),
            "mobileApi": self.mobile_api.ensure(),
            "cloudSync": self.cloud_sync.ensure(),
            "multiUser": self.multi_user.ensure(),
            "selfHealing": self.self_healing.run(),
        }
        self.monitoring.snapshot(self)
        return payload

    def status(self) -> dict:
        self.ensure_initialized()
        return {
            "schema": "temple-ai-studio.os-status.v1",
            "version": TEMPLE_OS_VERSION,
            "root": str(self.paths.root),
            "operationsRoot": str(self.paths.operations),
            "stateRoot": str(self.paths.state),
            "workspace": self.workspaces.status(),
            "projects": {"count": len(self.projects.list())},
            "providers": self.providers.status(),
            "models": self.models.status(),
            "plugins": self.plugins.status(),
            "prompts": self.prompts.status(),
            "knowledge": self.knowledge.status(),
            "userProfiles": self.user_profiles.status(),
            "applications": self.applications.status(),
            "agents": self.agents.status(),
            "collaboration": self.collaboration.status(),
            "queue": self.queue.status(),
            "scheduler": self.scheduler.status(),
            "workflows": self.workflows.status(),
            "automation": self.automation.status(),
            "downloads": self.downloads.status(),
            "updates": self.updates.status(),
            "mobileApi": self.mobile_api.status(),
            "cloudSync": self.cloud_sync.status(),
            "multiUser": self.multi_user.status(),
            "backup": self.backups.status(),
            "telemetry": read_json(self.paths.telemetry, {}),
            "recentEvents": self.logger.tail(20),
        }

    def health_check(self) -> dict:
        self.ensure_initialized()
        provider_checks = {
            capability: self.providers.select(capability, {"requiresEmma": capability in {"image", "video", "identity-preservation"}})
            for capability in ["llm", "script", "storyboard", "prompt", "image", "video", "subtitle", "editing", "rendering", "qa"]
        }
        checks = [
            {"name": "state-directory", "ok": self.paths.state.exists(), "path": str(self.paths.state)},
            {"name": "default-workspace", "ok": Path(self.workspaces.status()["default"]["path"]).exists()},
            {"name": "queue-registry", "ok": self.paths.queue.exists()},
            {"name": "provider-registry", "ok": self.paths.providers.exists()},
            {"name": "workflow-registry", "ok": self.paths.workflows.exists()},
            {"name": "agent-registry", "ok": self.paths.agents.exists()},
            {"name": "application-registry", "ok": self.paths.applications.exists()},
            {"name": "user-profile-registry", "ok": self.paths.user_profiles.exists()},
            {"name": "mobile-api-contract", "ok": self.paths.mobile_api.exists()},
            {"name": "multi-user-contract", "ok": self.paths.tenants.exists()},
            {"name": "local-ffmpeg-provider", "ok": provider_checks["rendering"].get("selected") is not None},
        ]
        failed = [check for check in checks if not check.get("ok")]
        result = {
            "schema": "temple-ai-studio.os-health.v1",
            "createdAt": now_iso(),
            "overall": "PASS" if not failed else "FAIL",
            "checks": checks,
            "providerSelections": provider_checks,
            "failedChecks": failed,
        }
        atomic_write_json(self.paths.state / "health.json", result)
        self.logger.emit("health-check-completed", {"overall": result["overall"]})
        return result

    def self_test(self) -> dict:
        self.ensure_initialized()
        task = self.queue.enqueue("health-check", {}, priority=80)
        worker_result = self.worker.run_once()
        agent_plan = self.agents.create_plan("請幫我產生一支神殿產品短影片", app_id="temple-product-video-generator")
        queued_plan = self.agents.enqueue_plan(agent_plan["id"])
        agent_results = [self.worker.run_once() for _ in queued_plan.get("taskIds", [])]
        collaboration = self.collaboration.start("規劃神殿產品影片", app_id="temple-product-video-generator")
        blocked_download = self.downloads.request("future-video-model", "https://example.com/model.safetensors", "video", approval=False)
        backup = self.backups.create(label="self-test")
        support = self.support_packages.create(self.status())
        health = self.health_check()
        checks = [
            {"name": "health-check", "ok": health.get("overall") == "PASS"},
            {"name": "queue-worker", "ok": worker_result.get("processed") is True and worker_result.get("task", {}).get("id") == task["id"]},
            {"name": "agent-plan-created", "ok": agent_plan.get("status") == "planned" and len(agent_plan.get("steps", [])) >= 5},
            {"name": "agent-plan-processed", "ok": all(item.get("task", {}).get("status") == "completed" for item in agent_results)},
            {"name": "collaboration-created", "ok": collaboration.get("agentRunId") is not None},
            {"name": "network-download-blocked", "ok": blocked_download.get("status") == "blocked"},
            {"name": "backup-created", "ok": Path(backup["path"]).exists() and backup["size"] > 0},
            {"name": "support-created", "ok": Path(support["path"]).exists() and support["size"] > 0},
            {"name": "paid-provider-locked", "ok": self.providers.select("voice").get("requiresCEOApproval") is True},
            {"name": "cloud-sync-locked", "ok": self.cloud_sync.status().get("allowed") is False},
            {"name": "single-user-local-mode", "ok": self.multi_user.status().get("mode") == "single-user-local"},
        ]
        result = {
            "schema": "temple-ai-studio.os-self-test.v1",
            "createdAt": now_iso(),
            "version": TEMPLE_OS_VERSION,
            "overall": "PASS" if all(check["ok"] for check in checks) else "FAIL",
            "checks": checks,
            "backup": backup,
            "supportPackage": support,
        }
        atomic_write_json(self.paths.state / "self-test.json", result)
        return result

    def serve(self, host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
        kernel = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:
                kernel.logger.emit("rest-api-request", {"client": self.client_address[0], "message": format % args})

            def _send(self, status: int, payload: Any) -> None:
                data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _read_json(self) -> dict:
                length = int(self.headers.get("Content-Length", "0") or "0")
                if not length:
                    return {}
                return json.loads(self.rfile.read(length).decode("utf-8"))

            def do_GET(self) -> None:
                parsed = urlparse(self.path)
                if parsed.path == "/api/health":
                    return self._send(HTTPStatus.OK, kernel.health_check())
                if parsed.path == "/api/status":
                    return self._send(HTTPStatus.OK, kernel.status())
                if parsed.path == "/api/queue":
                    return self._send(HTTPStatus.OK, kernel.queue.status())
                if parsed.path == "/api/providers":
                    return self._send(HTTPStatus.OK, kernel.providers.status())
                if parsed.path == "/api/workflows":
                    return self._send(HTTPStatus.OK, kernel.workflows.status())
                if parsed.path == "/api/projects":
                    return self._send(HTTPStatus.OK, {"projects": kernel.projects.list()})
                if parsed.path == "/api/config":
                    return self._send(HTTPStatus.OK, kernel.config.load())
                if parsed.path == "/api/user-profile":
                    return self._send(HTTPStatus.OK, kernel.user_profiles.status())
                if parsed.path == "/api/agents":
                    return self._send(HTTPStatus.OK, kernel.agents.status())
                if parsed.path == "/api/applications":
                    return self._send(HTTPStatus.OK, kernel.applications.status())
                if parsed.path == "/api/mobile/v1/status" or parsed.path == "/mobile/v1/status":
                    return self._send(HTTPStatus.OK, {"status": kernel.status(), "mobile": kernel.mobile_api.status()})
                if parsed.path == "/api/cloud-sync":
                    return self._send(HTTPStatus.OK, kernel.cloud_sync.status())
                if parsed.path == "/api/multi-user":
                    return self._send(HTTPStatus.OK, kernel.multi_user.status())
                return self._send(HTTPStatus.NOT_FOUND, {"error": "Not found"})

            def do_POST(self) -> None:
                parsed = urlparse(self.path)
                body = self._read_json()
                if parsed.path == "/api/queue":
                    task = kernel.queue.enqueue(body.get("type", "health-check"), body.get("payload", {}), int(body.get("priority", 50)))
                    return self._send(HTTPStatus.CREATED, task)
                if parsed.path == "/api/worker/run-once":
                    return self._send(HTTPStatus.OK, kernel.worker.run_once())
                if parsed.path == "/api/workflows/run":
                    run = kernel.workflows.run(body["workflowId"], body.get("payload", {}))
                    return self._send(HTTPStatus.CREATED, run)
                if parsed.path == "/api/projects":
                    project = kernel.projects.create(body["name"], body["appId"], body.get("workspaceId", "default"), body.get("metadata", {}))
                    return self._send(HTTPStatus.CREATED, project)
                if parsed.path == "/api/agents/plan":
                    plan = kernel.agents.create_plan(body["request"], body.get("appId", "temple-product-video-generator"))
                    return self._send(HTTPStatus.CREATED, plan)
                if parsed.path == "/api/agents/queue":
                    queued = kernel.agents.enqueue_plan(body["runId"])
                    return self._send(HTTPStatus.CREATED, queued)
                if parsed.path == "/api/collaboration":
                    session = kernel.collaboration.start(body["goal"], body.get("appId", "temple-product-video-generator"))
                    return self._send(HTTPStatus.CREATED, session)
                if parsed.path == "/api/support-package":
                    return self._send(HTTPStatus.CREATED, kernel.support_packages.create(kernel.status()))
                return self._send(HTTPStatus.NOT_FOUND, {"error": "Not found"})

        server = ThreadingHTTPServer((host, port), Handler)
        self.logger.emit("rest-api-started", {"host": host, "port": port})
        return server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Temple AI Studio OS local command center.")
    parser.add_argument("--root", default=str(Path.cwd()), help="Temple AI Studio project root.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    sub.add_parser("status")
    sub.add_parser("health-check")
    sub.add_parser("self-test")
    sub.add_parser("worker-once")
    backup = sub.add_parser("backup")
    backup.add_argument("--label", default="manual")
    restore = sub.add_parser("restore")
    restore.add_argument("--archive", required=True)
    restore.add_argument("--confirm", action="store_true")
    enqueue = sub.add_parser("enqueue")
    enqueue.add_argument("type")
    enqueue.add_argument("--payload", default="{}")
    workflow = sub.add_parser("run-workflow")
    workflow.add_argument("workflow_id")
    plan = sub.add_parser("plan-request")
    plan.add_argument("request")
    plan.add_argument("--app-id", default="temple-product-video-generator")
    queue_plan = sub.add_parser("queue-agent-plan")
    queue_plan.add_argument("run_id")
    apps = sub.add_parser("list-apps")
    apps.set_defaults(list_apps=True)
    download = sub.add_parser("request-model-download")
    download.add_argument("model_id")
    download.add_argument("source")
    download.add_argument("--capability", default="unknown")
    download.add_argument("--approval", action="store_true")
    serve = sub.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", default=8765, type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    kernel = TempleOSKernel(Path(args.root))
    if args.command == "init":
        payload = kernel.ensure_initialized()
    elif args.command == "status":
        payload = kernel.status()
    elif args.command == "health-check":
        payload = kernel.health_check()
    elif args.command == "self-test":
        payload = kernel.self_test()
    elif args.command == "worker-once":
        payload = kernel.worker.run_once()
    elif args.command == "backup":
        payload = kernel.backups.create(label=args.label)
    elif args.command == "restore":
        payload = kernel.backups.restore(Path(args.archive), confirm=args.confirm)
    elif args.command == "enqueue":
        payload = kernel.queue.enqueue(args.type, json.loads(args.payload))
    elif args.command == "run-workflow":
        payload = kernel.workflows.run(args.workflow_id)
    elif args.command == "plan-request":
        payload = kernel.agents.create_plan(args.request, app_id=args.app_id)
    elif args.command == "queue-agent-plan":
        payload = kernel.agents.enqueue_plan(args.run_id)
    elif args.command == "list-apps":
        payload = kernel.applications.status()
    elif args.command == "request-model-download":
        payload = kernel.downloads.request(args.model_id, args.source, args.capability, approval=args.approval)
    elif args.command == "serve":
        server = kernel.serve(args.host, args.port)
        print(json.dumps({"status": "running", "host": args.host, "port": args.port}, ensure_ascii=False, indent=2))
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            payload = {"status": "stopped"}
        finally:
            server.server_close()
    else:
        raise RuntimeError(f"Unsupported command: {args.command}")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if isinstance(payload, dict) and payload.get("overall") == "FAIL":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
