from __future__ import annotations

from typing import Any


def prepare_pm_crypto_updown_baseline_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prepared = []
    for row in rows:
        prepared.append(
            {
                **row,
                "market_probability_baseline": row["market_mid"],
                "no_skill_baseline": 0.5,
                "spot_lag_heuristic_candidate": _spot_lag_direction(row),
                "timestamp_shift_placebo_candidate": _timestamp_shift_placebo(row),
                "cost_spread_burden": row["market_spread"],
                "fill_caveat": _fill_caveat(row),
                "profitability_claimed": False,
                "direct_execution_allowed": False,
            }
        )
    return prepared


def _spot_lag_direction(row: dict[str, Any]) -> str:
    value = row.get("spot_return_5s")
    if value is None:
        return "NO_SIGNAL"
    if value > 0:
        return "UP"
    if value < 0:
        return "DOWN"
    return "FLAT"


def _timestamp_shift_placebo(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "placebo_type": "timestamp_shift",
        "shift_seconds": 15,
        "uses_future_information": False,
        "candidate_signal": "PLACEBO_ONLY",
        "source_event_ts": row["event_ts"],
    }


def _fill_caveat(row: dict[str, Any]) -> str:
    if "LOW_LIQUIDITY" in row["data_quality_flags"]:
        return "low_liquidity_no_fill_assumption_required"
    if "WIDE_SPREAD" in row["data_quality_flags"]:
        return "wide_spread_cost_sensitivity_required"
    return "fill_model_required_before_shadow_use"
