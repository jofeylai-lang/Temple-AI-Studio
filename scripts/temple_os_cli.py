from __future__ import annotations

import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from temple_ai_studio.temple_os import main


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
