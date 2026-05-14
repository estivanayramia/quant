from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    commands = [
        [sys.executable, "-m", "quant_os.cli", "research", "intake-source-policy"],
        [sys.executable, "-m", "quant_os.cli", "research", "intake-run"],
        [sys.executable, "-m", "quant_os.cli", "research", "knowledge-ledger-summary"],
        [sys.executable, "-m", "quant_os.cli", "research", "evidence-to-shadow-bridge"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "autonomy-milestones"],
    ]
    for command in commands:
        completed = subprocess.run(command, cwd=repo_root, check=False)
        if completed.returncode != 0:
            return completed.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
