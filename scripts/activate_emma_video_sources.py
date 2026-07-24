from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SCRIPTS_ROOT = Path(__file__).resolve().parent
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from temple_ai_studio.emma_video_activation import EmmaVideoActivation


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Activate approved Emma videos and canonical synthetic voice."
    )
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--production-root", required=True)
    parser.add_argument("--video-root", required=True)
    args = parser.parse_args()
    activation = EmmaVideoActivation(
        Path(args.project_root),
        Path(args.production_root),
        Path(args.video_root),
    )
    report = activation.run()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("overall") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
