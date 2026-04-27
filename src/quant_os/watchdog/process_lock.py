from __future__ import annotations

import json
import os
from pathlib import Path


class ProcessLockError(RuntimeError):
    pass


class ProcessLock:
    def __init__(self, path: str | Path = "reports/autonomy/daemon.lock") -> None:
        self.path = Path(path)
        self.acquired = False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            raise ProcessLockError(f"duplicate lock exists: {self.path}")
        self.path.write_text(json.dumps({"pid": os.getpid()}), encoding="utf-8")
        self.acquired = True

    def release(self) -> None:
        if self.acquired and self.path.exists():
            self.path.unlink()
        self.acquired = False

    def __enter__(self) -> ProcessLock:
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()


def lock_exists(path: str | Path = "reports/autonomy/daemon.lock") -> bool:
    return Path(path).exists()
