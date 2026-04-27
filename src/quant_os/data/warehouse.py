from __future__ import annotations

from pathlib import Path


def ensure_local_dirs() -> None:
    for path in [
        Path("data/demo"),
        Path("data/events"),
        Path("data/read_models"),
        Path("reports"),
    ]:
        path.mkdir(parents=True, exist_ok=True)
