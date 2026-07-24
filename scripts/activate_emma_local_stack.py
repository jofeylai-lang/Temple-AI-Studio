from __future__ import annotations

import argparse
import json
from pathlib import Path

from temple_ai_studio.provider_activation import (
    ProviderActivationManager,
    atomic_write_json,
    default_local_runtime_root,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Activate Emma's approved free local provider stack.")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--production-root", required=True)
    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()
    production_root = Path(args.production_root).resolve()
    workflow_root = production_root / "workflows"
    workflow_root.mkdir(parents=True, exist_ok=True)
    runtime_root = default_local_runtime_root()
    qwen_python = runtime_root / "qwen3-tts" / "Scripts" / "python.exe"
    musetalk_python = runtime_root / "musetalk" / "Scripts" / "python.exe"
    musetalk_root = production_root / "tools" / "MuseTalk"

    musetalk_descriptor = {
        "schema": "temple-ai-studio.local-command-production.v1",
        "id": "musetalk-1.5-production",
        "version": "1.0.0",
        "providerId": "musetalk-local",
        "productionReady": True,
        "requiredBindings": ["config", "output_dir", "output_file"],
        "allowedExecutableRoots": [str(runtime_root)],
        "workingDirectory": str(musetalk_root),
        "command": [
            str(musetalk_python),
            str(project_root / "scripts" / "musetalk_worker.py"),
            "--musetalk-root",
            str(musetalk_root),
            "--config",
            "{config}",
            "--output-dir",
            "{output_dir}",
            "--output-file",
            "{output_file}",
            "--ffmpeg-dir",
            str(production_root / "tools" / "ffmpeg"),
        ],
        "outputs": [{"mediaType": "video", "path": "{output_file}"}],
    }
    quality_descriptor = {
        "schema": "temple-ai-studio.local-command-production.v1",
        "id": "emma-quality-production",
        "version": "1.0.0",
        "providerId": "emma-quality-local",
        "productionReady": True,
        "requiredBindings": ["job", "output"],
        "allowedExecutableRoots": [str(runtime_root)],
        "workingDirectory": str(project_root),
        "command": [
            str(musetalk_python),
            str(project_root / "scripts" / "emma_quality_worker.py"),
            "--job",
            "{job}",
            "--output",
            "{output}",
        ],
        "outputs": [{"mediaType": "quality-report", "path": "{output}"}],
    }
    video_quality_descriptor = {
        "schema": "temple-ai-studio.local-command-production.v1",
        "id": "commercial-video-quality-production",
        "version": "1.0.0",
        "providerId": "commercial-video-evaluator-local",
        "productionReady": True,
        "requiredBindings": ["video", "output"],
        "allowedExecutableRoots": [str(runtime_root)],
        "workingDirectory": str(project_root),
        "command": [
            str(musetalk_python),
            str(project_root / "scripts" / "video_quality_worker.py"),
            "--video",
            "{video}",
            "--ffmpeg",
            str(production_root / "tools" / "ffmpeg" / "ffmpeg.exe"),
            "--syncnet",
            str(musetalk_root / "models" / "syncnet" / "latentsync_syncnet.pt"),
            "--openclip",
            str(production_root / "models" / "openclip-vit-b32" / "open_clip_pytorch_model.bin"),
            "--yunet",
            str(production_root / "models" / "opencv" / "face_detection_yunet_2023mar.onnx"),
            "--output",
            "{output}",
        ],
        "outputs": [{"mediaType": "quality-report", "path": "{output}"}],
    }
    atomic_write_json(workflow_root / "musetalk-production.json", musetalk_descriptor)
    atomic_write_json(workflow_root / "emma-quality-production.json", quality_descriptor)
    atomic_write_json(
        workflow_root / "commercial-quality-production.json",
        video_quality_descriptor,
    )

    manager = ProviderActivationManager(production_root / "providers")
    manager.initialize()
    defaults = {item["id"]: item for item in manager.defaults()["providers"]}
    for provider_id in [
        "qwen3-tts-local",
        "qwen3-voice-design-local",
        "musetalk-local",
        "emma-quality-local",
        "commercial-video-evaluator-local",
    ]:
        default = defaults[provider_id]
        changes = {
            key: default[key]
            for key in [
                "enabled",
                "python",
                "modelPath",
                "workerPath",
                "runtimePath",
                "entryPoint",
                "modelRoot",
                "commandDescriptor",
            ]
            if key in default
        }
        manager.configure_provider(provider_id, changes)
    billing = manager.emergency_disable_billing()
    health = {
        provider_id: manager.test_connection(provider_id, timeout=30)
        for provider_id in [
            "qwen3-tts-local",
            "qwen3-voice-design-local",
            "musetalk-local",
        "emma-quality-local",
        "commercial-video-evaluator-local",
        ]
    }
    result = {
        "schema": "temple-ai-studio.emma-local-stack-activation.v1",
        "overall": "PASS"
        if billing["billingEnabled"] is False
        and all(item["overall"] == "PASS" for item in health.values())
        else "FAIL",
        "billing": {
            **billing,
            "monthlyLimitTwd": 0,
            "perJobLimitTwd": 0,
        },
        "health": health,
        "descriptors": {
            "musetalk": str(workflow_root / "musetalk-production.json"),
            "emmaQuality": str(workflow_root / "emma-quality-production.json"),
            "videoQuality": str(workflow_root / "commercial-quality-production.json"),
        },
    }
    report = production_root / "emma" / "reports" / "local-stack-activation.json"
    atomic_write_json(report, result)
    print(json.dumps({**result, "report": str(report)}, ensure_ascii=False, indent=2))
    return 0 if result["overall"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
