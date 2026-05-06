from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_os.data.prediction_markets.history import sha256_file

SCHEMA_VERSION = "1.0"
DEFAULT_LANE_ID = "short_dated_clean_binary"
LANE_ACTIVITY_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
}


def load_lane_activity_history(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = "lane activity fixture must contain a JSON object"
        raise ValueError(msg)
    return payload


def build_lane_activity_history(
    fixture_path: str | Path,
    *,
    lane_id: str = DEFAULT_LANE_ID,
) -> dict[str, Any]:
    path = Path(fixture_path)
    payload = load_lane_activity_history(path)
    source_hash = sha256_file(path)
    return build_lane_activity_history_from_payload(
        payload,
        source_path=path,
        source_hash=source_hash,
        lane_id=lane_id,
    )


def build_lane_activity_history_from_payload(
    payload: dict[str, Any],
    *,
    source_path: str | Path,
    source_hash: str,
    lane_id: str = DEFAULT_LANE_ID,
) -> dict[str, Any]:
    path = Path(source_path)
    source_mode = str(payload.get("source_mode") or "fixture")
    raw_payload_sha256 = str(payload.get("raw_payload_sha256") or source_hash)
    markets = [
        _normalize_market(
            raw,
            source_path=path,
            source_hash=source_hash,
            raw_payload_sha256=raw_payload_sha256,
            source_mode=source_mode,
            target_lane_id=lane_id,
        )
        for raw in payload.get("markets", [])
        if isinstance(raw, dict)
    ]
    markets = sorted(markets, key=lambda item: item["market_id"])
    included = [market for market in markets if market["included_in_lane_activity_research"]]
    observation_count = sum(len(market["activity"]) for market in markets)
    included_observation_count = sum(len(market["activity"]) for market in included)
    resolution_summary = _resolution_summary(markets)
    activity_source_mode_counts = _activity_source_mode_counts(markets, fallback=source_mode)
    depth_status = _activity_depth_status(
        included_market_count=len(included),
        included_observation_count=included_observation_count,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": "prediction_lane_activity_" + source_hash[:20],
        "dataset_hash": source_hash,
        "generated_at": _iso_or_none(payload.get("captured_at")) or _now_utc(),
        "sequence": str(payload.get("sequence") or "24"),
        "source": str(payload.get("source") or "polymarket"),
        "source_mode": source_mode,
        "source_path": str(path),
        "source_sha256": source_hash,
        "raw_payload_sha256": raw_payload_sha256,
        "lane_id": lane_id,
        "market_count": len(markets),
        "included_market_count": len(included),
        "resolved_market_count": resolution_summary["resolved_count"],
        "unresolved_market_count": resolution_summary["unresolved_count"],
        "ambiguous_market_count": resolution_summary["ambiguous_count"],
        "excluded_market_count": resolution_summary["excluded_count"],
        "activity_observation_count": observation_count,
        "included_activity_observation_count": included_observation_count,
        "activity_source_mode_counts": activity_source_mode_counts,
        "raw_event_count": int(payload.get("raw_event_count") or observation_count),
        "usable_event_count": int(payload.get("usable_event_count") or observation_count),
        "malformed_event_count": int(payload.get("malformed_event_count") or 0),
        "activity_depth_status": depth_status,
        "resolution_summary": resolution_summary,
        "markets": markets,
        "observed_facts": [
            "Lane activity dataset is built from saved fixtures only.",
            "Within-market price, liquidity, volume, lifecycle, and wallet-flow observations are preserved.",
        ],
        "inferred_patterns": [
            "The dataset can support dynamic lane research but not execution authority.",
        ],
        "unknowns": [
            "Fixture activity depth is still too limited to establish profitability or replay realism.",
            "Wallet-flow fields are heuristic research context and do not identify causal alpha.",
        ],
        **LANE_ACTIVITY_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _normalize_market(
    raw: dict[str, Any],
    *,
    source_path: Path,
    source_hash: str,
    raw_payload_sha256: str,
    source_mode: str,
    target_lane_id: str,
) -> dict[str, Any]:
    activity = sorted(
        [_normalize_activity(item) for item in raw.get("activity", []) if isinstance(item, dict)],
        key=lambda item: item["timestamp"] or "",
    )
    resolution = _normalize_resolution(raw.get("resolution") or {})
    raw_lane_id = str(raw.get("lane_id") or "")
    binary = bool(raw.get("binary", False))
    quality_gate = str(raw.get("quality_gate") or "UNKNOWN")
    exclusion_reason = _exclusion_reason(
        raw_lane_id=raw_lane_id,
        target_lane_id=target_lane_id,
        binary=binary,
        quality_gate=quality_gate,
        resolution=resolution,
        activity=activity,
    )
    included = exclusion_reason is None
    return {
        "market_id": str(raw.get("market_id") or ""),
        "condition_id": str(raw.get("condition_id") or ""),
        "slug": str(raw.get("slug") or ""),
        "question": str(raw.get("question") or ""),
        "category": str(raw.get("category") or "unknown"),
        "lane_id": raw_lane_id,
        "quality_gate": quality_gate,
        "binary": binary,
        "opened_at": _iso_or_none(raw.get("opened_at")),
        "end_time": _iso_or_none(raw.get("end_time")),
        "resolution_time": _iso_or_none(raw.get("resolution_time")),
        "reference_context": raw.get("reference_context") or {},
        "resolution": resolution,
        "activity": activity,
        "included_in_lane_activity_research": included,
        "lane_activity_status": _lane_activity_status(included=included, resolution=resolution),
        "candidate_inclusion_reason": raw.get("candidate_inclusion_reason"),
        "exclusion_reason": exclusion_reason,
        "activity_density": {
            "usable_event_count": len(activity),
            "source_mode": source_mode,
        },
        "provenance": {
            "source_path": str(source_path),
            "source_sha256": source_hash,
            "raw_payload_sha256": raw_payload_sha256,
            "source_mode": source_mode,
        },
    }


def _normalize_activity(raw: dict[str, Any]) -> dict[str, Any]:
    yes_buy_volume = _float(raw.get("yes_buy_volume"))
    no_buy_volume = _float(raw.get("no_buy_volume"))
    one_sided_flow_ratio = raw.get("one_sided_flow_ratio")
    if one_sided_flow_ratio in {None, ""}:
        total_side_volume = yes_buy_volume + no_buy_volume
        one_sided_flow_ratio = (
            max(yes_buy_volume, no_buy_volume) / total_side_volume
            if total_side_volume > 0
            else 0.0
        )
    return {
        "timestamp": _iso_or_none(raw.get("timestamp")),
        "lifecycle_status": str(raw.get("lifecycle_status") or "UNKNOWN"),
        "hours_to_resolution": _float(raw.get("hours_to_resolution")),
        "yes_price": _float(raw.get("yes_price")),
        "no_price": _float(raw.get("no_price")),
        "volume": _float(raw.get("volume")),
        "liquidity": _float(raw.get("liquidity")),
        "wallet_count": int(_float(raw.get("wallet_count"))),
        "new_wallet_count": int(_float(raw.get("new_wallet_count"))),
        "dominant_wallet_share": _float(raw.get("dominant_wallet_share")),
        "wallet_concentration": _float(raw.get("wallet_concentration")),
        "yes_buy_volume": yes_buy_volume,
        "no_buy_volume": no_buy_volume,
        "one_sided_flow_ratio": round(float(one_sided_flow_ratio), 6),
        "source_event_id": raw.get("source_event_id") or raw.get("event_id"),
        "event_type": raw.get("event_type"),
        "source_mode": raw.get("source_mode"),
        "activity_quality_flags": raw.get("activity_quality_flags") or [],
    }


def _normalize_resolution(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": str(raw.get("status") or "UNKNOWN"),
        "winning_outcome": raw.get("winning_outcome"),
        "resolved_at": _iso_or_none(raw.get("resolved_at")),
        "truth_source": raw.get("truth_source"),
        "confidence": str(raw.get("confidence") or "UNKNOWN"),
    }


def _exclusion_reason(
    *,
    raw_lane_id: str,
    target_lane_id: str,
    binary: bool,
    quality_gate: str,
    resolution: dict[str, Any],
    activity: list[dict[str, Any]],
) -> str | None:
    if raw_lane_id != target_lane_id:
        return "OUTSIDE_TARGET_LANE"
    if not binary:
        return "AMBIGUOUS_MARKET_STRUCTURE"
    if quality_gate != "RESEARCHABLE":
        return quality_gate
    if resolution["status"] in {"AMBIGUOUS", "DISPUTED"}:
        return resolution["status"]
    if not activity:
        return "MISSING_ACTIVITY_HISTORY"
    return None


def _lane_activity_status(*, included: bool, resolution: dict[str, Any]) -> str:
    if not included:
        return "EXCLUDED"
    if resolution["status"] == "RESOLVED":
        return "INCLUDED_RESOLVED"
    return "INCLUDED_UNSCORED"


def _resolution_summary(markets: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "resolved_count": 0,
        "unresolved_count": 0,
        "ambiguous_count": 0,
        "disputed_count": 0,
        "excluded_count": 0,
    }
    for market in markets:
        status = market["resolution"]["status"]
        if status == "RESOLVED":
            counts["resolved_count"] += 1
        elif status == "UNRESOLVED":
            counts["unresolved_count"] += 1
        elif status == "AMBIGUOUS":
            counts["ambiguous_count"] += 1
        elif status == "DISPUTED":
            counts["disputed_count"] += 1
        if not market["included_in_lane_activity_research"]:
            counts["excluded_count"] += 1
    return counts


def _activity_source_mode_counts(
    markets: list[dict[str, Any]],
    *,
    fallback: str,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for market in markets:
        for observation in market["activity"]:
            mode = str(observation.get("source_mode") or fallback)
            counts[mode] = counts.get(mode, 0) + 1
    return dict(sorted(counts.items()))


def _activity_depth_status(
    *,
    included_market_count: int,
    included_observation_count: int,
) -> str:
    if included_market_count <= 0:
        return "LANE_ACTIVITY_EMPTY"
    average_depth = included_observation_count / included_market_count
    if average_depth >= 5:
        return "LANE_ACTIVITY_ENRICHED"
    if average_depth >= 3:
        return "LANE_ACTIVITY_PARTIAL"
    return "LANE_ACTIVITY_TOO_THIN"


def _iso_or_none(value: Any) -> str | None:
    if value in {None, ""}:
        return None
    text = str(value)
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    timestamp = datetime.fromisoformat(text)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return timestamp.astimezone(UTC).isoformat()


def _now_utc() -> str:
    return datetime.now(UTC).isoformat()


def _float(value: Any) -> float:
    if value in {None, ""}:
        return 0.0
    return float(value)
