from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from quant_os.core.events import DomainEvent

_APPEND_LOCK = threading.Lock()


class JsonlEventStore:
    def __init__(self, path: str | Path = "data/events/events.jsonl") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: DomainEvent) -> None:
        payload = (event.model_dump_json() + "\n").encode("utf-8")
        with _APPEND_LOCK:
            fd = os.open(self.path, os.O_APPEND | os.O_CREAT | os.O_WRONLY)
            try:
                os.write(fd, payload)
            finally:
                os.close(fd)

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
