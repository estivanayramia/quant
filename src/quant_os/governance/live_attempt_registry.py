from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_os.core.ids import deterministic_id

ATTEMPTS_PATH = Path("reports/live_canary/live_attempt_registry.json")


def create_live_attempt_record(
    *,
    symbol: str,
    notional_usd: float,
    status: str,
    blockers: list[str] | None = None,
    client_order_id: str | None = None,
    fake_mode: bool = False,
) -> dict[str, Any]:
    timestamp = datetime.now(UTC).isoformat()
    return {
        "attempt_id": deterministic_id("live_attempt", symbol, notional_usd, timestamp, length=20),
        "created_at": timestamp,
        "symbol": symbol,
        "notional_usd": notional_usd,
        "status": status,
        "blockers": blockers or [],
        "client_order_id": client_order_id,
        "fake_mode": fake_mode,
        "real_order_attempted": False,
        "live_promotion_status": "LIVE_BLOCKED",
    }


def append_live_attempt(
    record: dict[str, Any],
    path: str | Path = ATTEMPTS_PATH,
) -> dict[str, Any]:
    records = load_live_attempts(path)
    records.append(record)
    registry_path = Path(path)
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"attempts": records, "latest_attempt": record}
    registry_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def load_live_attempts(path: str | Path = ATTEMPTS_PATH) -> list[dict[str, Any]]:
    registry_path = Path(path)
    if not registry_path.exists():
        return []
    try:
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return list(payload.get("attempts", []))


def latest_live_attempt(path: str | Path = ATTEMPTS_PATH) -> dict[str, Any] | None:
    records = load_live_attempts(path)
    return records[-1] if records else None

