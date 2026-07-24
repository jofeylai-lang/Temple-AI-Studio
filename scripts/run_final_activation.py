from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parent
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from temple_ai_studio.commercial_acceptance import CommercialAcceptanceSystem, FinalReleaseManager
from temple_ai_studio.emma_production import EmmaProductionActivator
from temple_ai_studio.provider_activation import ProviderActivationManager
from temple_ai_studio.production_workflow import (
    ProductionWorkflowBlocked,
    RealProductionWorkflow,
)
from temple_ai_studio.real_providers import create_comfy_workflow_descriptor


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_production_root() -> Path:
    configured = os.environ.get("TEMPLE_PRODUCTION_DATA_ROOT")
    if configured:
        return Path(configured).resolve()
    return (project_root().parent / "Temple AI Studio Production Data").resolve()


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Temple AI Studio final production activation.")
    result.add_argument("--production-root", default=str(default_production_root()))
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    commands.add_parser("status")
    scan = commands.add_parser("scan-emma")
    scan.add_argument("--copy", action="store_true")
    commands.add_parser("prepare-emma")
    activate = commands.add_parser("activate-emma")
    activate.add_argument("--identity-artifact", required=True)
    activate.add_argument("--voice-profile", required=True)
    activate.add_argument("--validation-evidence", required=True)
    rollback = commands.add_parser("rollback-emma")
    rollback.add_argument("--version", required=True)
    rollback.add_argument("--confirmation", required=True)
    health = commands.add_parser("provider-health")
    health.add_argument("--include-disabled", action="store_true")
    declaration = commands.add_parser("declare-commercial-license")
    declaration.add_argument("provider_id")
    declaration.add_argument("--statement", required=True)
    descriptor = commands.add_parser("set-provider-descriptor")
    descriptor.add_argument("provider_id")
    descriptor.add_argument("--path", required=True)
    billing = commands.add_parser("authorize-billing")
    billing.add_argument("--approval-reference", required=True)
    billing.add_argument("--monthly-limit-twd", required=True, type=float)
    billing.add_argument("--per-job-limit-twd", required=True, type=float)
    commands.add_parser("emergency-stop-billing")
    secret = commands.add_parser("store-provider-secret")
    secret.add_argument("provider_id")
    secret.add_argument("--value")
    commands.add_parser("production-preflight")
    workflow = commands.add_parser("run-production")
    workflow.add_argument("--request", required=True)
    wrap = commands.add_parser("wrap-comfy-workflow")
    wrap.add_argument("--source", required=True)
    wrap.add_argument("--output", required=True)
    wrap.add_argument("--id", required=True)
    wrap.add_argument("--provider-id", required=True)
    wrap.add_argument("--binding", action="append", default=[])
    wrap.add_argument("--required-binding", action="append", default=[])
    acceptance = commands.add_parser("acceptance")
    acceptance.add_argument("--manifest", action="append", default=[])
    release = commands.add_parser("release")
    release.add_argument("--version", required=True)
    return result


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    root = Path(args.production_root).resolve()
    emma = EmmaProductionActivator(project_root(), root / "emma")
    providers = ProviderActivationManager(root / "providers")
    acceptance = CommercialAcceptanceSystem(project_root(), root)
    if args.command == "init":
        payload = {
            "emma": emma.initialize(),
            "providers": providers.initialize(),
            "acceptance": acceptance.initialize(),
        }
    elif args.command == "status":
        payload = acceptance.readiness()
    elif args.command == "scan-emma":
        payload = emma.scan_intake(copy_files=args.copy)
    elif args.command == "prepare-emma":
        payload = emma.prepare_adapters()
    elif args.command == "activate-emma":
        payload = emma.activate_version(
            Path(args.identity_artifact),
            Path(args.voice_profile),
            Path(args.validation_evidence),
        )
    elif args.command == "rollback-emma":
        payload = emma.rollback(args.version, args.confirmation)
    elif args.command == "provider-health":
        providers.initialize()
        payload = providers.test_all(include_disabled=args.include_disabled)
    elif args.command == "declare-commercial-license":
        payload = providers.declare_commercial_eligibility(
            args.provider_id,
            args.statement,
        )
    elif args.command == "set-provider-descriptor":
        provider = providers.provider(args.provider_id)
        key = (
            "workflowDescriptor"
            if provider.get("kind") == "comfyui-workflow"
            else "commandDescriptor"
        )
        payload = providers.configure_provider(
            args.provider_id,
            {key: str(Path(args.path).resolve())},
        )
    elif args.command == "authorize-billing":
        payload = providers.authorize_billing(
            args.approval_reference,
            args.monthly_limit_twd,
            args.per_job_limit_twd,
        )
    elif args.command == "emergency-stop-billing":
        payload = providers.emergency_disable_billing()
    elif args.command == "store-provider-secret":
        value = args.value or getpass.getpass("API 金鑰（輸入內容不顯示）: ")
        payload = providers.store_secret(args.provider_id, value)
    elif args.command == "production-preflight":
        payload = RealProductionWorkflow(project_root(), root).preflight()
    elif args.command == "run-production":
        request = json.loads(Path(args.request).read_text(encoding="utf-8-sig"))
        try:
            payload = RealProductionWorkflow(project_root(), root).run(request)
        except ProductionWorkflowBlocked as error:
            payload = error.report
    elif args.command == "wrap-comfy-workflow":
        bindings = {}
        for raw in args.binding:
            if "=" not in raw or ":" not in raw.rsplit("=", 1)[-1]:
                raise ValueError(
                    f"Invalid binding '{raw}'. Expected NAME=NODE:INPUT."
                )
            name, target_text = raw.split("=", 1)
            node, input_name = target_text.rsplit(":", 1)
            if not name or not node or not input_name:
                raise ValueError(
                    f"Invalid binding '{raw}'. Expected NAME=NODE:INPUT."
                )
            target = {"node": node, "input": input_name}
            current = bindings.get(name)
            if current is None:
                bindings[name] = target
            elif isinstance(current, list):
                current.append(target)
            else:
                bindings[name] = [current, target]
        payload = create_comfy_workflow_descriptor(
            Path(args.source),
            Path(args.output),
            args.id,
            args.provider_id,
            bindings,
            args.required_binding,
        )
    elif args.command == "acceptance":
        paths = [Path(item).resolve() for item in args.manifest] if args.manifest else None
        payload = acceptance.evaluate(paths)
    elif args.command == "release":
        payload = FinalReleaseManager(project_root(), root).create_release(args.version)
    else:
        raise RuntimeError(f"Unsupported command: {args.command}")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if payload.get("overall") == "BLOCKED":
        return 2
    return 0 if payload.get("overall") != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
