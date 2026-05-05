from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np
import pandas as pd


def calibration_diagnostics(
    *,
    probabilities: list[float],
    outcomes: list[int],
    expected_returns_bps: list[float],
    equity_curve: list[float],
    regimes: list[str],
) -> dict[str, Any]:
    probs = np.array([min(0.999, max(0.001, value)) for value in probabilities], dtype="float64")
    actual = np.array(outcomes, dtype="float64")
    brier = float(np.mean((probs - actual) ** 2)) if len(probs) else 0.0
    log_loss = (
        float(-np.mean(actual * np.log(probs) + (1.0 - actual) * np.log(1.0 - probs)))
        if len(probs)
        else 0.0
    )
    expectancy = float(np.mean(expected_returns_bps)) if expected_returns_bps else 0.0
    equity = pd.Series(equity_curve, dtype="float64")
    drawdown = _max_drawdown(equity)
    regime_sensitivity = _regime_sensitivity(expected_returns_bps, regimes)
    return {
        "brier_score": brier,
        "log_loss": log_loss,
        "calibration_curve": _calibration_curve(probs.tolist(), outcomes),
        "expectancy_after_costs": expectancy,
        "drawdown": drawdown,
        "walk_forward_stability": _walk_forward_stability(expected_returns_bps),
        "regime_sensitivity": regime_sensitivity,
        "live_trading_enabled": False,
    }


def _calibration_curve(probabilities: list[float], outcomes: list[int]) -> list[dict[str, float | int]]:
    buckets: dict[int, list[tuple[float, int]]] = defaultdict(list)
    for probability, outcome in zip(probabilities, outcomes, strict=False):
        buckets[min(9, int(probability * 10))].append((probability, outcome))
    curve = []
    for bucket, values in sorted(buckets.items()):
        curve.append(
            {
                "bucket": bucket,
                "mean_probability": float(np.mean([item[0] for item in values])),
                "empirical_rate": float(np.mean([item[1] for item in values])),
                "count": len(values),
            }
        )
    return curve


def _max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    return float((equity / equity.cummax() - 1.0).min())


def _walk_forward_stability(values: list[float]) -> float:
    if not values:
        return 0.0
    mean = float(np.mean(values))
    std = float(np.std(values))
    return float(abs(mean) / (1.0 + std))


def _regime_sensitivity(values: list[float], regimes: list[str]) -> dict[str, float]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for value, regime in zip(values, regimes, strict=False):
        grouped[regime].append(value)
    return {regime: float(np.mean(items)) for regime, items in sorted(grouped.items())}
