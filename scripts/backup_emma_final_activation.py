from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


SCRIPTS_ROOT = Path(__file__).resolve().parent
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from temple_ai_studio.final_activation_recovery import (
    FinalActivationBackupManager,
    RESTORE_CONFIRMATION,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Back up and validate final Emma activation.")
    parser.add_argument("--production-root", required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("create")
    restore = commands.add_parser("restore-test")
    restore.add_argument("--archive", required=True)
    restore.add_argument("--target")
    args = parser.parse_args()
    manager = FinalActivationBackupManager(Path(args.production_root))
    if args.command == "create":
        payload = manager.create()
    else:
        target = (
            Path(args.target)
            if args.target
            else Path(args.production_root)
            / "recovery-tests"
            / f"emma-final-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        )
        payload = manager.restore(
            Path(args.archive),
            target,
            RESTORE_CONFIRMATION,
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("overall") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
