from __future__ import annotations

from typing import Any


def build_time_series_features(dataset: dict[str, Any]) -> list[dict[str, Any]]:
    features = [
        _market_time_series_features(market)
        for market in dataset["markets"]
        if market["included_in_lane_activity_research"] and market["activity"]
    ]
    return sorted(features, key=lambda item: item["market_id"])


def _market_time_series_features(market: dict[str, Any]) -> dict[str, Any]:
    activity = sorted(market["activity"], key=lambda item: item["timestamp"] or "")
    first = activity[0]
    latest = activity[-1]
    previous = activity[-2] if len(activity) > 1 else first
    middle = activity[len(activity) // 2]
    current_probability = round(float(latest["yes_price"]), 6)
    label = _prediction_label(market["resolution"])
    price_deltas = [
        round(float(current["yes_price"]) - float(prior["yes_price"]), 6)
        for prior, current in zip(activity, activity[1:], strict=False)
    ]
    liquidity_deltas = [
        round(float(current["liquidity"]) - float(prior["liquidity"]), 6)
        for prior, current in zip(activity, activity[1:], strict=False)
    ]
    unsupported_jumps = [
        abs(price_delta)
        for price_delta, liquidity_delta in zip(price_deltas, liquidity_deltas, strict=False)
        if liquidity_delta <= 0
    ]
    wallet_counts = [max(int(item["wallet_count"]), 1) for item in activity]
    new_wallet_ratios = [
        float(item["new_wallet_count"]) / wallet_count
        for item, wallet_count in zip(activity, wallet_counts, strict=False)
    ]
    one_sided_flow = [float(item["one_sided_flow_ratio"]) for item in activity]
    dominant_wallet_shares = [float(item["dominant_wallet_share"]) for item in activity]
    latest_hours = float(latest["hours_to_resolution"])
    return {
        "market_id": market["market_id"],
        "condition_id": market["condition_id"],
        "slug": market["slug"],
        "category": market["category"],
        "lane_id": market["lane_id"],
        "prediction_timestamp": latest["timestamp"],
        "feature_family": "lane_activity_time_series_v1",
        "activity_observation_count": len(activity),
        "current_market_probability": current_probability,
        "naive_probability": 0.5,
        "simple_calibrated_probability": _simple_calibrated_probability(current_probability),
        "first_yes_price": round(float(first["yes_price"]), 6),
        "middle_yes_price": round(float(middle["yes_price"]), 6),
        "latest_yes_price": current_probability,
        "full_price_drift": round(current_probability - float(first["yes_price"]), 6),
        "mid_to_close_drift": round(current_probability - float(middle["yes_price"]), 6),
        "late_price_slope": round(current_probability - float(previous["yes_price"]), 6),
        "max_abs_price_step": round(max([abs(item) for item in price_deltas] or [0.0]), 6),
        "max_unsupported_price_jump": round(max(unsupported_jumps or [0.0]), 6),
        "liquidity": round(float(latest["liquidity"]), 6),
        "liquidity_change": round(float(latest["liquidity"]) - float(first["liquidity"]), 6),
        "liquidity_change_pct": _pct_change(float(first["liquidity"]), float(latest["liquidity"])),
        "volume": round(float(latest["volume"]), 6),
        "volume_change": round(float(latest["volume"]) - float(first["volume"]), 6),
        "wallet_count": int(latest["wallet_count"]),
        "wallet_concentration": round(float(latest["wallet_concentration"]), 6),
        "wallet_concentration_change": round(
            float(latest["wallet_concentration"]) - float(first["wallet_concentration"]),
            6,
        ),
        "dominant_wallet_share": round(float(latest["dominant_wallet_share"]), 6),
        "dominant_wallet_persistence": round(
            sum(1 for share in dominant_wallet_shares if share >= 0.5) / len(dominant_wallet_shares),
            6,
        ),
        "new_wallet_entry_burst": round(max(new_wallet_ratios or [0.0]), 6),
        "one_sided_flow_spike": round(max(one_sided_flow or [0.0]), 6),
        "latest_hours_to_resolution": round(latest_hours, 6),
        "latest_time_to_resolution_bucket": _time_to_resolution_bucket(latest_hours),
        "event_time_decay": round(1.0 / (1.0 + max(latest_hours, 0.0)), 6),
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


def _pct_change(first: float, latest: float) -> float:
    if first == 0:
        return 0.0
    return round((latest - first) / first, 6)


def _time_to_resolution_bucket(hours: float) -> str:
    if hours <= 6:
        return "FINAL_HOURS"
    if hours <= 24:
        return "NEAR_CLOSE"
    if hours <= 72:
        return "SHORT"
    return "LONGER"
