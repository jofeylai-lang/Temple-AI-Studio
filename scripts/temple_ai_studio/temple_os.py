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
        self.rules = BusinessRuleEngine(self.config)
        self.queue = QueueManager(self.paths, self.rules, self.logger)
        self.scheduler = TaskScheduler(self.paths, self.queue, self.logger)
        self.workflows = WorkflowEngine(self.paths, self.queue, self.logger)
        self.automation = AutomationEngine(self.paths, self.queue, self.logger)
        self.backups = BackupManager(self.paths, self.logger)
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
            "queue": self.queue.ensure(),
            "schedules": self.scheduler.ensure(),
            "workflows": self.workflows.ensure(),
            "automation": self.automation.ensure(),
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
            "queue": self.queue.status(),
            "scheduler": self.scheduler.status(),
            "workflows": self.workflows.status(),
            "automation": self.automation.status(),
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
        backup = self.backups.create(label="self-test")
        support = self.support_packages.create(self.status())
        health = self.health_check()
        checks = [
            {"name": "health-check", "ok": health.get("overall") == "PASS"},
            {"name": "queue-worker", "ok": worker_result.get("processed") is True and worker_result.get("task", {}).get("id") == task["id"]},
            {"name": "backup-created", "ok": Path(backup["path"]).exists() and backup["size"] > 0},
            {"name": "support-created", "ok": Path(support["path"]).exists() and support["size"] > 0},
            {"name": "paid-provider-locked", "ok": self.providers.select("voice").get("requiresCEOApproval") is True},
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
