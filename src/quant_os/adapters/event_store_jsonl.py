from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from quant_os.core.events import DomainEvent

_APPEND_LOCK = threading.Lock()


class JsonlEventStore:
    def __init__(self, path: str | Path = "data/events/events.jsonl") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: DomainEvent) -> None:
        payload = event.model_dump_json() + "\n"
        with (
            _APPEND_LOCK,
            _locked_append(self.path),
            self.path.open("a", encoding="utf-8") as handle,
        ):
            handle.write(payload)
            handle.flush()

    def read_all(self) -> list[DomainEvent]:
        if not self.path.exists():
            return []
        events: list[DomainEvent] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if stripped:
                    events.append(DomainEvent.model_validate(json.loads(stripped)))
        return events

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()


@contextmanager
def _locked_append(path: Path) -> Iterator[None]:
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as lock_file:
        if _is_windows():
            import msvcrt

            msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _is_windows() -> bool:
    import os

    return os.name == "nt"
