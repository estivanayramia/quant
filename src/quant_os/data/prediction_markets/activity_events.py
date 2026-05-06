from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Any

from quant_os.data.prediction_markets.activity_schema import (
    ACTIVITY_EVENT_TYPES,
    CRITICAL_EVENT_FIELDS,
)

ACTIVITY_EVENT_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
}


def normalize_activity_events(payload: dict[str, Any]) -> dict[str, Any]:
    raw_events = [event for event in payload.get("events", []) if isinstance(event, dict)]
    normalized = [_normalize_event(event, source_mode=str(payload.get("source_mode") or "fixture")) for event in raw_events]
    usable = sorted(
        [event for event in normalized if event["usable"]],
        key=lambda item: (item["timestamp"], item["event_id"]),
    )
    rejected = sorted(
        [event for event in normalized if not event["usable"]],
        key=lambda item: item["event_id"],
    )
    return {
        "source": payload.get("source", "polymarket"),
        "source_mode": payload.get("source_mode", "fixture"),
        "raw_event_count": len(raw_events),
        "usable_event_count": len(usable),
        "malformed_event_count": len(rejected),
        "timestamp_problem_count": sum(
            1 for event in rejected if "BAD_TIMESTAMP" in event["quality_flags"]
        ),
        "missing_critical_field_count": sum(
            1 for event in rejected if any(flag.startswith("MISSING_") for flag in event["quality_flags"])
        ),
        "event_type_counts": dict(Counter(event["event_type"] for event in usable)),
        "events": usable,
        "rejected_events": rejected,
        **ACTIVITY_EVENT_SAFETY,
    }


def _normalize_event(raw: dict[str, Any], *, source_mode: str) -> dict[str, Any]:
    flags = _quality_flags(raw)
    timestamp = _iso_or_none(raw.get("timestamp"))
    if timestamp is None:
        flags.append("BAD_TIMESTAMP")
    event_type = str(raw.get("event_type") or "UNKNOWN")
    if event_type not in ACTIVITY_EVENT_TYPES:
        flags.append("UNKNOWN_EVENT_TYPE")
    usable = not flags
    return {
        "event_id": str(raw.get("event_id") or ""),
        "market_id": str(raw.get("market_id") or ""),
        "condition_id": str(raw.get("condition_id") or ""),
        "slug": str(raw.get("slug") or ""),
        "timestamp": timestamp or "",
        "event_type": event_type,
        "outcome": str(raw.get("outcome") or "").upper() or None,
        "side": str(raw.get("side") or "").lower() or None,
        "price": _float(raw.get("price")),
        "size": _float(raw.get("size")),
        "volume": _float(raw.get("volume")),
        "liquidity": _float(raw.get("liquidity")),
        "wallet": str(raw.get("wallet")).lower() if raw.get("wallet") else None,
        "wallet_count": int(_float(raw.get("wallet_count"))),
        "new_wallet_count": int(_float(raw.get("new_wallet_count"))),
        "dominant_wallet_share": _float(raw.get("dominant_wallet_share")),
        "wallet_concentration": _float(raw.get("wallet_concentration")),
        "source_mode": source_mode,
        "quality_flags": sorted(set(flags)),
        "usable": usable,
    }


def _quality_flags(raw: dict[str, Any]) -> list[str]:
    flags = []
    for field in CRITICAL_EVENT_FIELDS:
        if raw.get(field) in {None, ""}:
            flags.append(f"MISSING_{field.upper()}")
    return flags


def _iso_or_none(value: Any) -> str | None:
    if value in {None, ""}:
        return None
    try:
        text = str(value)
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        timestamp = datetime.fromisoformat(text)
    except ValueError:
        return None
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return timestamp.astimezone(UTC).isoformat()


def _float(value: Any) -> float:
    if value in {None, ""}:
        return 0.0
    return float(value)
