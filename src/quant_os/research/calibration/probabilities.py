from __future__ import annotations

import math


def estimate_signal_probability(
    *,
    raw_score: float,
    volatility_regime: str,
    liquidity_score: float,
    overextension_z: float,
) -> float:
    regime_adjustment = {"low": 0.15, "normal": 0.0, "high": -0.25}.get(volatility_regime, -0.05)
    liquidity_adjustment = (max(0.0, min(1.0, liquidity_score)) - 0.5) * 0.9
    overextension_adjustment = -max(0.0, abs(overextension_z) - 1.5) * 0.25
    logit = (raw_score - 0.5) * 3.0 + regime_adjustment + liquidity_adjustment + overextension_adjustment
    probability = 1.0 / (1.0 + math.exp(-logit))
    return float(max(0.01, min(0.99, probability)))
