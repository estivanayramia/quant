from __future__ import annotations


def estimate_uncertainty(
    *,
    sample_size: int,
    regime_observations: int,
    feature_stability: float,
) -> float:
    sample_penalty = 1.0 / (1.0 + max(0, sample_size) / 100.0)
    regime_penalty = 1.0 / (1.0 + max(0, regime_observations) / 30.0)
    instability = 1.0 - max(0.0, min(1.0, feature_stability))
    return float(max(0.0, min(1.0, sample_penalty * 0.4 + regime_penalty * 0.35 + instability * 0.25)))
