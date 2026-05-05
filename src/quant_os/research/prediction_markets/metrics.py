from __future__ import annotations

import math
from typing import Any

FORECAST_DEFINITIONS = {
    "naive_50_50": {
        "probability_key": "naive_probability",
        "description": "No-skill 50/50 probability baseline.",
        "kind": "baseline",
    },
    "current_market_probability": {
        "probability_key": "current_market_probability",
        "description": "Latest saved market-implied probability baseline.",
        "kind": "baseline",
    },
    "simple_calibrated_heuristic": {
        "probability_key": "simple_calibrated_probability",
        "description": "Transparent shrinkage heuristic toward 50/50.",
        "kind": "baseline",
    },
    "quality_adjusted_candidate": {
        "probability_key": "quality_adjusted_probability",
        "description": "Transparent liquidity and wallet-concentration shrinkage candidate.",
        "kind": "candidate",
    },
}


def evaluate_candidate_forecasts(features: list[dict[str, Any]]) -> dict[str, Any]:
    resolved = [item for item in features if item["prediction_label"] is not None]
    baselines = {}
    candidates = {}
    for name, definition in FORECAST_DEFINITIONS.items():
        score = score_probability_forecast(
            resolved,
            probability_key=definition["probability_key"],
            description=definition["description"],
        )
        if definition["kind"] == "baseline":
            baselines[name] = score
        else:
            candidates[name] = score
    return {
        "resolved_observation_count": len(resolved),
        "feature_count": len(features),
        "baselines": baselines,
        "candidates": candidates,
        "confidence_warnings": _confidence_warnings(resolved),
        "observed_facts": [
            "Forecast metrics use only markets with attached resolution truth.",
            "Unresolved markets are retained in features but excluded from scored metrics.",
        ],
        "inferred_patterns": [
            "Accuracy, Brier score, and log loss are screening diagnostics, not alpha evidence.",
        ],
        "unknowns": [
            "Sample counts are still limited and cannot establish profitability or replay realism.",
        ],
    }


def score_probability_forecast(
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
            "log_loss": None,
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
    log_loss = sum(
        _log_loss(float(item[probability_key]), int(item["prediction_label"])) for item in resolved
    ) / len(resolved)
    return {
        "description": description,
        "brier_score": round(float(brier), 6),
        "accuracy": round(float(accuracy), 6),
        "log_loss": round(float(log_loss), 6),
        "observation_count": len(resolved),
        "opaque_model": False,
    }


def beats_on_brier(candidate: dict[str, Any], baseline: dict[str, Any]) -> bool:
    if candidate["brier_score"] is None or baseline["brier_score"] is None:
        return False
    return float(candidate["brier_score"]) < float(baseline["brier_score"])


def _log_loss(probability: float, label: int) -> float:
    probability = min(max(probability, 1e-6), 1.0 - 1e-6)
    if label == 1:
        return -math.log(probability)
    return -math.log(1.0 - probability)


def _confidence_warnings(resolved: list[dict[str, Any]]) -> list[str]:
    warnings = []
    if len(resolved) < 20:
        warnings.append("RESOLVED_SAMPLE_BELOW_REPLAY_DESIGN_THRESHOLD")
    categories = {item["category"] for item in resolved}
    if len(categories) < 4:
        warnings.append("CATEGORY_COVERAGE_NARROW")
    return warnings
