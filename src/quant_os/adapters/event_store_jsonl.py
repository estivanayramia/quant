from __future__ import annotations

import json
from pathlib import Path

from quant_os.core.events import DomainEvent


class JsonlEventStore:
    def __init__(self, path: str | Path = "data/events/events.jsonl") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: DomainEvent) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(event.model_dump_json() + "\n")

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
