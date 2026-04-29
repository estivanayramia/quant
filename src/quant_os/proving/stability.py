from __future__ import annotations

from typing import Any


def compute_strategy_stability(records: list[dict[str, Any]]) -> dict[str, Any]:
    top_values = [item.get("top_strategy_id") for item in records if item.get("top_strategy_id")]
    if len(top_values) < 2:
        return {
            "status": "UNAVAILABLE",
            "top_strategy_flip_rate": 0.0,
            "top_strategy_sequence": top_values,
            "leaderboard_hash_changes": 0,
            "warnings": ["INSUFFICIENT_HISTORY_FOR_STABILITY"],
        }
    flips = sum(
        1
        for previous, current in zip(top_values, top_values[1:], strict=False)
        if previous != current
    )
    hash_values = [item.get("leaderboard_hash") for item in records if item.get("leaderboard_hash")]
    hash_changes = sum(
        1
        for previous, current in zip(hash_values, hash_values[1:], strict=False)
        if previous != current
    )
    flip_rate = flips / max(len(top_values) - 1, 1)
    warnings = ["TOP_STRATEGY_FLIP_RATE_HIGH"] if flip_rate > 0.5 else []
    return {
        "status": "WARN" if warnings else "PASS",
        "top_strategy_flip_rate": flip_rate,
        "top_strategy_sequence": top_values,
        "leaderboard_hash_changes": hash_changes,
        "warnings": warnings,
    }
