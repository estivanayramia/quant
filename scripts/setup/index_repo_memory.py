"""Index this repository with codebase-memory-mcp.

The index is local-only and stored under the ignored `.cbm-cache/` directory.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CBM_EXE = REPO_ROOT / "tools" / "codebase-memory-mcp" / "extracted" / "codebase-memory-mcp.exe"
CBM_CACHE_DIR = REPO_ROOT / ".cbm-cache"


def main() -> int:
    if not CBM_EXE.exists():
        raise SystemExit(f"Missing codebase-memory-mcp binary: {CBM_EXE}")

    env = os.environ.copy()
    env["CBM_CACHE_DIR"] = str(CBM_CACHE_DIR)
    payload = {"repo_path": REPO_ROOT.as_posix()}
    result = subprocess.run(
        [str(CBM_EXE), "cli", "index_repository", json.dumps(payload)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=180,
    )
    print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip())
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
