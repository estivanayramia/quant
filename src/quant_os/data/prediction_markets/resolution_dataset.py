from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from quant_os.data.prediction_markets.history import (
    load_prediction_market_history,
    sha256_file,
)

SCHEMA_VERSION = "1.0"


def build_resolution_aware_dataset(fixture_path: str | Path) -> dict[str, Any]:
    path = Path(fixture_path)
    payload = load_prediction_market_history(path)
    source_hash = sha256_file(path)
    markets = [_normalize_market(raw, source_path=path, source_hash=source_hash) for raw in payload["markets"]]
    markets = sorted(markets, key=lambda item: item["market_id"])
    resolution_summary = _resolution_summary(markets)
    snapshot_count = sum(len(market["snapshots"]) for market in markets)
    included = [market for market in markets if market["included_in_candidate_research"]]
    return {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": "prediction_history_" + source_hash[:20],
        "generated_at": datetime.now(UTC).isoformat(),
        "sequence": "21",
        "source": "polymarket",
        "source_mode": str(payload.get("source_mode") or "fixture"),
        "source_path": str(path),
        "source_sha256": source_hash,
        "market_count": len(markets),
        "included_market_count": len(included),
        "snapshot_count": snapshot_count,
        "resolution_summary": resolution_summary,
        "markets": markets,
        "observed_facts": [
            "Dataset is built from saved prediction-market history fixtures only.",
            "Lifecycle snapshots, market state, reference context, and resolution truth are preserved.",
        ],
        "inferred_patterns": [
            "Only clean binary markets are eligible for candidate prediction research.",
        ],
        "unknowns": [
            "Fixture history is too narrow to prove edge, calibration quality, or replay realism.",
        ],
        "live_trading_enabled": False,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "execution_authority": "NONE",
        "evidence_only": True,
    }


def _normalize_market(raw: dict[str, Any], *, source_path: Path, source_hash: str) -> dict[str, Any]:
    snapshots = sorted(
        [_normalize_snapshot(snapshot) for snapshot in raw.get("snapshots", []) if isinstance(snapshot, dict)],
        key=lambda item: item["timestamp"],
    )
    binary = bool(raw.get("binary", False))
    quality_gate = str(raw.get("quality_gate") or "UNKNOWN")
    resolution = _normalize_resolution(raw.get("resolution") or {})
    exclusion_reason = _exclusion_reason(binary=binary, quality_gate=quality_gate, resolution=resolution)
    return {
        "market_id": str(raw.get("market_id") or ""),
        "condition_id": str(raw.get("condition_id") or ""),
        "slug": str(raw.get("slug") or ""),
        "question": str(raw.get("question") or ""),
        "category": str(raw.get("category") or "unknown"),
        "quality_gate": quality_gate,
        "binary": binary,
        "opened_at": _iso_or_none(raw.get("opened_at")),
        "end_time": _iso_or_none(raw.get("end_time")),
        "resolution_time": _iso_or_none(raw.get("resolution_time")),
        "reference_context": raw.get("reference_context") or {},
        "resolution": resolution,
        "snapshots": snapshots,
        "included_in_candidate_research": exclusion_reason is None,
        "exclusion_reason": exclusion_reason,
        "provenance": {
            "source_path": str(source_path),
            "source_sha256": source_hash,
            "source_mode": "fixture" if "tests/fixtures" in str(source_path).replace("\\", "/") else "cached",
        },
    }


def _normalize_snapshot(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp": _iso_or_none(raw.get("timestamp")),
        "lifecycle_status": str(raw.get("lifecycle_status") or "UNKNOWN"),
        "yes_price": _float(raw.get("yes_price")),
        "no_price": _float(raw.get("no_price")),
        "volume": _float(raw.get("volume")),
        "liquidity": _float(raw.get("liquidity")),
        "wallet_concentration": _float(raw.get("wallet_concentration")),
    }


def _normalize_resolution(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": str(raw.get("status") or "UNKNOWN"),
        "winning_outcome": raw.get("winning_outcome"),
        "resolved_at": _iso_or_none(raw.get("resolved_at")),
        "truth_source": raw.get("truth_source"),
        "confidence": str(raw.get("confidence") or "UNKNOWN"),
    }


def _exclusion_reason(*, binary: bool, quality_gate: str, resolution: dict[str, Any]) -> str | None:
    if not binary:
        return "AMBIGUOUS_MARKET_STRUCTURE"
    if quality_gate != "RESEARCHABLE":
        return quality_gate
    if resolution["status"] in {"AMBIGUOUS", "DISPUTED"}:
        return resolution["status"]
    return None


def _resolution_summary(markets: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"resolved_count": 0, "unresolved_count": 0, "ambiguous_count": 0, "disputed_count": 0}
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
    return counts


def _iso_or_none(value: Any) -> str | None:
    if value in {None, ""}:
        return None
    timestamp = pd.Timestamp(value)
    if pd.isna(timestamp):
        return None
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    return timestamp.tz_convert("UTC").isoformat()


def _float(value: Any) -> float:
    if value in {None, ""}:
        return 0.0
    return float(value)
