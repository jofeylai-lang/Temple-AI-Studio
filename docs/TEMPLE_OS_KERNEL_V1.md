# Temple AI Studio OS Kernel V1

## Purpose

Temple OS Kernel V1 is the shared operating layer for Temple AI Studio applications.
It is not a standalone product. It provides the reusable runtime services that future Temple applications can call instead of rebuilding infrastructure.

## Implemented Services

- Configuration Center
- Workspace Manager
- Project Manager
- Provider Manager
- Model Manager
- Plugin Manager and local Plugin SDK manifest validation
- Prompt Library
- Knowledge Base
- Business Rule Engine
- Queue Manager
- Task Scheduler
- Workflow Engine
- Automation Engine
- Background Worker
- Self-healing stale task recovery
- Monitoring and local telemetry snapshot
- Local JSONL logging
- Backup Manager
- Restore Manager with explicit confirmation
- Support package generator with secret redaction
- Local REST API
- Local CLI

## Local CLI

Run from the project root:

```powershell
python -B scripts\temple_os_cli.py --root "D:\AI\Jofey AI Studio" status
python -B scripts\temple_os_cli.py --root "D:\AI\Jofey AI Studio" health-check
python -B scripts\temple_os_cli.py --root "D:\AI\Jofey AI Studio" self-test
python -B scripts\temple_os_cli.py --root "D:\AI\Jofey AI Studio" backup --label manual
```

Start the local REST API:

```powershell
python -B scripts\temple_os_cli.py --root "D:\AI\Jofey AI Studio" serve --host 127.0.0.1 --port 8765
```

One-click launch file:

```text
start_temple_ai_studio.bat
```

## REST API

Local-only endpoints:

- `GET /api/health`
- `GET /api/status`
- `GET /api/queue`
- `GET /api/providers`
- `GET /api/workflows`
- `GET /api/projects`
- `GET /api/config`
- `POST /api/queue`
- `POST /api/worker/run-once`
- `POST /api/workflows/run`
- `POST /api/projects`
- `POST /api/support-package`

## Safety Rules

- Paid providers remain locked unless explicitly approved.
- Cloud sync remains locked unless explicitly approved.
- External telemetry is disabled.
- Destructive operations are blocked by the Business Rule Engine.
- Restore requires explicit confirmation.
- Support packages exclude product photos, generated media, private exports and secrets.

## Product Video Generator Integration

Temple Product Video Generator now exposes Temple OS status through `/api/health`.

Every export package includes:

```text
temple_os.json
```

This records platform version, provider registry, queue status, workflow status, backup status and recent local events.

## Current Boundary

The OS Kernel is local-first and production-usable for one-machine operation.

Future cloud sync, multi-user deployment, paid providers, mobile API hosting and online model downloads require CEO approval before activation.
