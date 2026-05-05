from __future__ import annotations

from typing import Any

import pandas as pd


def parameter_stability_warnings(split_results: list[dict[str, Any]]) -> list[str]:
    params = [float(item["selected_min_edge_bps"]) for item in split_results]
    if not params:
        return ["NO_PARAMETER_EVIDENCE"]
    if len(set(params)) > 1:
        return ["UNSTABLE_PARAMETERS"]
    return []


def edge_degradation_warnings(
    split_results: list[dict[str, Any]],
    *,
    degradation_threshold_bps: float = 2.0,
    min_oos_expectancy_bps: float = 0.0,
) -> list[str]:
    if not split_results:
        return ["NO_OOS_EVIDENCE"]
    train = pd.Series(
        [float(item["train_metrics"]["expectancy_after_costs_bps"]) for item in split_results],
        dtype="float64",
    )
    test = pd.Series(
        [float(item["test_metrics"]["expectancy_after_costs_bps"]) for item in split_results],
        dtype="float64",
    )
    warnings: list[str] = []
    if float(train.mean() - test.mean()) > degradation_threshold_bps:
        warnings.append("EDGE_DEGRADATION")
    if float(test.mean()) < min_oos_expectancy_bps:
        warnings.append("OOS_EXPECTANCY_BELOW_THRESHOLD")
    positive = test.clip(lower=0.0)
    if positive.sum() > 0 and positive.max() / positive.sum() > 0.75:
        warnings.append("EDGE_CONCENTRATED_IN_ONE_WINDOW")
    return warnings


def regime_summary(split_results: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    buckets: dict[str, list[float]] = {}
    for item in split_results:
        regime = str(item.get("dominant_test_regime") or "unknown")
        buckets.setdefault(regime, []).append(
            float(item["test_metrics"]["expectancy_after_costs_bps"])
        )
    return {
        regime: {
            "split_count": float(len(values)),
            "mean_test_expectancy_after_costs_bps": float(pd.Series(values).mean()),
        }
        for regime, values in sorted(buckets.items())
    }
