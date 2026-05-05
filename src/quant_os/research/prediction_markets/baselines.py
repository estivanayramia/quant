from __future__ import annotations

from typing import Any


def evaluate_prediction_baselines(features: list[dict[str, Any]]) -> dict[str, Any]:
    resolved = [item for item in features if item["prediction_label"] is not None]
    baselines = {
        "naive_50_50": _score_baseline(
            resolved,
            probability_key="naive_probability",
            description="No-skill 50/50 probability baseline.",
        ),
        "current_market_probability": _score_baseline(
            resolved,
            probability_key="current_market_probability",
            description="Latest saved market-implied probability baseline.",
        ),
        "simple_calibrated_heuristic": _score_baseline(
            resolved,
            probability_key="simple_calibrated_probability",
            description="Transparent shrinkage heuristic toward 50/50 for tiny samples.",
        ),
    }
    return {
        "resolved_observation_count": len(resolved),
        "feature_count": len(features),
        "baselines": baselines,
        "observed_facts": [
            "Baseline metrics use only markets with attached resolution truth.",
            "Unresolved markets are retained as features but excluded from scored metrics.",
        ],
        "inferred_patterns": [
            "Brier score and directional accuracy are screening diagnostics, not alpha evidence.",
        ],
        "unknowns": [
            "The sample is too small for reliable calibration or strategy selection.",
        ],
    }


def _score_baseline(
    resolved: list[dict[str, Any]],
    *,
    probability_key: str,
    description: str,
) -> dict[str, Any]:
    if not resolved:
        return {
            "description": description,
            "brier_score": None,
            "accuracy": None,
            "observation_count": 0,
            "opaque_model": False,
        }
    brier = sum(
        (float(item[probability_key]) - float(item["prediction_label"])) ** 2 for item in resolved
    ) / len(resolved)
    accuracy = sum(
        int((float(item[probability_key]) >= 0.5) == bool(item["prediction_label"]))
        for item in resolved
    ) / len(resolved)
    return {
        "description": description,
        "brier_score": round(float(brier), 6),
        "accuracy": round(float(accuracy), 6),
        "observation_count": len(resolved),
        "opaque_model": False,
    }
