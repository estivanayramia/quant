from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


class Heartbeat:
    def __init__(self, path: str | Path = "reports/heartbeat.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def start(self, run_id: str) -> dict[str, object]:
        payload = {"run_id": run_id, "status": "running", "started_at": _now()}
        self._write(payload)
        return payload

    def complete(self, status: str = "completed") -> dict[str, object]:
        payload = self.read()
        payload.update({"status": status, "completed_at": _now()})
        self._write(payload)
        return payload

    def read(self) -> dict[str, object]:
        if not self.path.exists():
            return {"status": "missing"}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, payload: dict[str, object]) -> None:
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _now() -> str:
    return datetime.now(UTC).isoformat()
