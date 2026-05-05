from __future__ import annotations

from datetime import datetime
from typing import Any


def build_prediction_features(dataset: dict[str, Any]) -> list[dict[str, Any]]:
    features = [
        _market_features(market)
        for market in dataset["markets"]
        if market["included_in_candidate_research"] and market.get("snapshots")
    ]
    return sorted(features, key=lambda item: item["market_id"])


def _market_features(market: dict[str, Any]) -> dict[str, Any]:
    snapshots = sorted(market["snapshots"], key=lambda item: item["timestamp"])
    first = snapshots[0]
    latest = snapshots[-1]
    previous = snapshots[-2] if len(snapshots) > 1 else first
    opened_at = _parse_time(market["opened_at"])
    prediction_time = _parse_time(latest["timestamp"])
    end_time = _parse_time(market["end_time"])
    current_probability = round(float(latest["yes_price"]), 6)
    price_drift = round(current_probability - float(first["yes_price"]), 6)
    recent_drift = round(current_probability - float(previous["yes_price"]), 6)
    label = _prediction_label(market["resolution"])
    time_to_resolution = round((end_time - prediction_time).total_seconds() / 3600.0, 6)
    market_age = round((prediction_time - opened_at).total_seconds() / 3600.0, 6)
    heuristic_probability = _simple_calibrated_probability(current_probability)
    return {
        "market_id": market["market_id"],
        "condition_id": market["condition_id"],
        "slug": market["slug"],
        "category": market["category"],
        "prediction_timestamp": latest["timestamp"],
        "feature_family": "interpretable_market_state_v1",
        "current_market_probability": current_probability,
        "naive_probability": 0.5,
        "simple_calibrated_probability": heuristic_probability,
        "price_drift_from_open": price_drift,
        "recent_price_drift": recent_drift,
        "market_age_hours": market_age,
        "time_to_resolution_hours": time_to_resolution,
        "nearing_close": latest["lifecycle_status"] == "NEARING_CLOSE" or time_to_resolution <= 72.0,
        "liquidity": round(float(latest["liquidity"]), 6),
        "volume": round(float(latest["volume"]), 6),
        "wallet_concentration": round(float(latest["wallet_concentration"]), 6),
        "thinness_penalty": 1.0 if float(latest["liquidity"]) < 1_000.0 else 0.0,
        "ambiguous_market_penalty": 0.0,
        "prediction_label": label,
        "resolution_status": market["resolution"]["status"],
        "observed_market_data": True,
        "attached_resolution_truth": label is not None,
    }


def _simple_calibrated_probability(current_probability: float) -> float:
    return round((current_probability * 0.75) + 0.125, 6)


def _prediction_label(resolution: dict[str, Any]) -> int | None:
    if resolution["status"] != "RESOLVED":
        return None
    if resolution.get("winning_outcome") == "YES":
        return 1
    if resolution.get("winning_outcome") == "NO":
        return 0
    return None


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
