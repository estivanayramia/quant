from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from quant_os.data.prediction_markets.activity_events import normalize_activity_events
from quant_os.data.prediction_markets.activity_history import (
    DEFAULT_LANE_ID,
    build_lane_activity_history_from_payload,
)
from quant_os.data.prediction_markets.history import sha256_file
from quant_os.data.prediction_markets.polymarket_activity_provider import (
    PolymarketActivityProvider,
)

ACTIVITY_CAPTURE_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
}
CAPTURE_REPORT_ROOT = Path("reports/sequence25/activity_capture")
CAPTURE_ARTIFACT_ROOT = Path("data/prediction_markets/activity_capture")


def load_activity_capture(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = "activity capture artifact must contain a JSON object"
        raise ValueError(msg)
    return payload


def capture_polymarket_activity(
    *,
    fixture_path: str | Path | None,
    output_root: str | Path = ".",
    manual_network: bool = False,
    explicit_network_ack: bool = False,
) -> dict[str, Any]:
    if fixture_path is None:
        if not manual_network:
            return _blocked("MANUAL_NETWORK_NOT_REQUESTED")
        if not explicit_network_ack:
            return _blocked("EXPLICIT_NETWORK_ACK_REQUIRED")
        provider = PolymarketActivityProvider(http_client=None)
        return provider.fetch_activity(
            lane_id=DEFAULT_LANE_ID,
            manual_network=manual_network,
            explicit_network_ack=explicit_network_ack,
        )

    raw_path = Path(fixture_path)
    raw_payload = load_activity_capture(raw_path)
    raw_hash = sha256_file(raw_path)
    normalized_artifact = _normalized_activity_artifact(
        raw_payload,
        source_path=raw_path,
        source_hash=raw_hash,
    )
    output = Path(output_root)
    artifact_root = output / CAPTURE_ARTIFACT_ROOT
    artifact_root.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_root / "latest_polymarket_activity_capture.json"
    artifact_path.write_text(
        json.dumps(normalized_artifact, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    payload = {
        "sequence": "25",
        "status": "CAPTURED_FROM_SAVED_ARTIFACT",
        "source": raw_payload.get("source", "polymarket"),
        "source_mode": raw_payload.get("source_mode", "fixture"),
        "lane_id": raw_payload.get("lane_id", DEFAULT_LANE_ID),
        "source_endpoint": raw_payload.get("source_endpoint"),
        "captured_at": raw_payload.get("captured_at"),
        "raw_payload_sha256": raw_hash,
        "raw_event_count": normalized_artifact["raw_event_count"],
        "usable_event_count": normalized_artifact["usable_event_count"],
        "malformed_event_count": normalized_artifact["malformed_event_count"],
        "normalized_artifact": normalized_artifact,
        "artifact_path": str(artifact_path),
        "observed_facts": [
            "Polymarket activity capture used a saved artifact only.",
            "No authenticated endpoints, signing, or trading endpoints are used.",
        ],
        "inferred_patterns": [
            "Real-cached activity can improve lane research inputs without granting execution authority.",
        ],
        "unknowns": [
            "Saved public activity is not a complete fill, fee, or queue-position model.",
        ],
        **ACTIVITY_CAPTURE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }
    payload["report_paths"] = _write_capture_report(payload, output_root=output_root)
    return payload


def build_activity_dataset_from_capture(
    fixture_path: str | Path,
    *,
    lane_id: str = DEFAULT_LANE_ID,
) -> dict[str, Any]:
    path = Path(fixture_path)
    raw_payload = load_activity_capture(path)
    raw_hash = sha256_file(path)
    artifact = _normalized_activity_artifact(
        raw_payload,
        source_path=path,
        source_hash=raw_hash,
    )
    dataset = build_lane_activity_history_from_payload(
        artifact,
        source_path=path,
        source_hash=raw_hash,
        lane_id=lane_id,
    )
    dataset["real_activity_status"] = (
        "REAL_CACHED_ACTIVITY_PRESENT"
        if dataset["source_mode"] == "real_cached"
        else "REAL_ACTIVITY_NOT_PRESENT"
    )
    return dataset


def _normalized_activity_artifact(
    payload: dict[str, Any],
    *,
    source_path: Path,
    source_hash: str,
) -> dict[str, Any]:
    normalized = normalize_activity_events(payload)
    events_by_market: dict[str, list[dict[str, Any]]] = {}
    for event in normalized["events"]:
        events_by_market.setdefault(event["market_id"], []).append(event)
    markets = []
    for market in payload.get("markets", []):
        if not isinstance(market, dict):
            continue
        market_id = str(market.get("market_id") or "")
        activity = [
            _event_to_activity(event, market=market)
            for event in sorted(events_by_market.get(market_id, []), key=lambda item: item["timestamp"])
        ]
        markets.append({**market, "activity": activity})
    return {
        "sequence": str(payload.get("sequence") or "25"),
        "source": payload.get("source", "polymarket"),
        "source_mode": payload.get("source_mode", "fixture"),
        "captured_at": payload.get("captured_at"),
        "source_endpoint": payload.get("source_endpoint"),
        "capture_mode": payload.get("capture_mode"),
        "lane_id": payload.get("lane_id", DEFAULT_LANE_ID),
        "source_path": str(source_path),
        "source_sha256": source_hash,
        "raw_payload_sha256": source_hash,
        "raw_event_count": normalized["raw_event_count"],
        "usable_event_count": normalized["usable_event_count"],
        "malformed_event_count": normalized["malformed_event_count"],
        "timestamp_problem_count": normalized["timestamp_problem_count"],
        "missing_critical_field_count": normalized["missing_critical_field_count"],
        "event_type_counts": normalized["event_type_counts"],
        "markets": markets,
        "rejected_events": normalized["rejected_events"],
    }


def _event_to_activity(event: dict[str, Any], *, market: dict[str, Any]) -> dict[str, Any]:
    price = float(event["price"])
    size = float(event["size"])
    outcome = event.get("outcome")
    side = event.get("side")
    yes_buy_volume = size if outcome == "YES" and side == "buy" else 0.0
    no_buy_volume = size if outcome == "NO" and side == "buy" else 0.0
    return {
        "timestamp": event["timestamp"],
        "lifecycle_status": _lifecycle_status(event),
        "hours_to_resolution": _hours_to_resolution(
            timestamp=event["timestamp"],
            end_time=str(market.get("end_time") or ""),
        ),
        "yes_price": price,
        "no_price": round(1.0 - price, 6),
        "volume": event["volume"],
        "liquidity": event["liquidity"],
        "wallet_count": event["wallet_count"],
        "new_wallet_count": event["new_wallet_count"],
        "dominant_wallet_share": event["dominant_wallet_share"],
        "wallet_concentration": event["wallet_concentration"],
        "yes_buy_volume": yes_buy_volume,
        "no_buy_volume": no_buy_volume,
        "one_sided_flow_ratio": round(max(price, 1.0 - price), 6),
        "source_event_id": event["event_id"],
        "event_type": event["event_type"],
        "source_mode": event["source_mode"],
        "activity_quality_flags": event["quality_flags"],
    }


def _lifecycle_status(event: dict[str, Any]) -> str:
    if event["event_type"] == "resolution_update":
        return "CLOSED"
    if event["event_type"] == "market_lifecycle_update":
        return "CLOSED"
    return "NEARING_CLOSE"


def _hours_to_resolution(*, timestamp: str, end_time: str) -> float:
    if not timestamp or not end_time:
        return 0.0
    if end_time.endswith("Z"):
        end_time = f"{end_time[:-1]}+00:00"
    start = datetime.fromisoformat(timestamp)
    end = datetime.fromisoformat(end_time)
    return round(max((end - start).total_seconds() / 3600.0, 0.0), 6)


def _blocked(reason: str) -> dict[str, Any]:
    return {
        "sequence": "25",
        "status": "BLOCKED",
        "reason": reason,
        "network_fetch_attempted": False,
        **ACTIVITY_CAPTURE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _write_capture_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / CAPTURE_REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_activity_capture.json"
    md_path = root / "latest_activity_capture.md"
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    lines = [
        "# Sequence 25 Polymarket Activity Capture",
        "",
        "Research-only activity capture report. No execution authority.",
        "",
        f"Status: {payload['status']}",
        f"Source mode: {payload['source_mode']}",
        f"Raw events: {payload['raw_event_count']}",
        f"Usable events: {payload['usable_event_count']}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Observed facts",
    ]
    lines.extend(f"- {item}" for item in payload["observed_facts"])
    lines.extend(["", "## Inferred patterns"])
    lines.extend(f"- {item}" for item in payload["inferred_patterns"])
    lines.extend(["", "## Unknowns"])
    lines.extend(f"- {item}" for item in payload["unknowns"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
