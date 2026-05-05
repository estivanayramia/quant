from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_os.core.ids import deterministic_id

LIVE_SESSION_PATH = Path("reports/live_canary/live_session_registry.json")


def append_live_session_event(
    event_type: str,
    details: dict[str, Any] | None = None,
    path: str | Path = LIVE_SESSION_PATH,
) -> dict[str, Any]:
    session_path = Path(path)
    events = load_live_session_events(session_path)
    timestamp = datetime.now(UTC).isoformat()
    event = {
        "event_id": deterministic_id("live_session", event_type, timestamp, length=20),
        "event_type": event_type,
        "timestamp": timestamp,
        "details": details or {},
        "live_promotion_status": "LIVE_BLOCKED",
    }
    events.append(event)
    session_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"events": events, "latest_event": event}
    session_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def load_live_session_events(path: str | Path = LIVE_SESSION_PATH) -> list[dict[str, Any]]:
    session_path = Path(path)
    if not session_path.exists():
        return []
    try:
        payload = json.loads(session_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return list(payload.get("events", []))

