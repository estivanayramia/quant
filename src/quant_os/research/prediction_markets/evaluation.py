from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.data.prediction_markets.resolution_dataset import build_resolution_aware_dataset
from quant_os.research.prediction_markets.features import build_prediction_features
from quant_os.research.prediction_markets.lane_selection import select_prediction_lanes
from quant_os.research.prediction_markets.market_strata import build_market_strata
from quant_os.research.prediction_markets.metrics import score_probability_forecast
from quant_os.research.prediction_markets.signal_families import (
    SIGNAL_FAMILIES,
    apply_signal_families,
)

LANE_EVALUATION_ROOT = Path("reports/sequence23/lane_evaluation")
PREDICTION_CANDIDATE_ROOT = Path("reports/sequence23/prediction_candidates")
LANE_EVALUATION_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
}
MIN_LANE_RESOLVED_OBSERVATIONS = 6
SIGNAL_BRIER_MARGIN = 0.01


def evaluate_lanes(dataset: dict[str, Any]) -> dict[str, Any]:
    strata = build_market_strata(dataset)
    lane_selection = select_prediction_lanes(dataset=dataset, strata=strata)
    features = apply_signal_families(build_prediction_features(dataset))
    features_by_id = {feature["market_id"]: feature for feature in features}
    lane_evaluations = [
        _evaluate_lane(lane, features_by_id=features_by_id) for lane in lane_selection["lanes"]
    ]
    lane_evaluations = sorted(lane_evaluations, key=lambda item: item["rank"])
    best_lane_evaluation = next(
        (
            lane
            for lane in lane_evaluations
            if lane["lane_status"] not in {"BROAD_LANE_REJECTED", "LANE_TOO_THIN", "EMPTY_LANE"}
        ),
        lane_evaluations[0] if lane_evaluations else None,
    )
    credible = [
        lane
        for lane in lane_evaluations
        if any(result["credible_signal_family"] for result in lane["candidate_results"].values())
    ]
    status = "CANDIDATE_SIGNAL_DISCOVERED" if credible else "NO_CREDIBLE_SIGNAL_FAMILY"
    return {
        "sequence": "23",
        "source": "polymarket",
        "source_mode": dataset["source_mode"],
        "dataset_summary": {
            "dataset_id": dataset["dataset_id"],
            "dataset_hash": dataset["dataset_hash"],
            "market_count": dataset["market_count"],
            "included_market_count": dataset["included_market_count"],
            "snapshot_count": dataset["snapshot_count"],
            "resolution_summary": dataset["resolution_summary"],
        },
        "lane_evaluation_status": status,
        "best_lane_evaluation": best_lane_evaluation,
        "lane_evaluations": lane_evaluations,
        "signal_families_tested": [family["signal_family_id"] for family in SIGNAL_FAMILIES],
        "observed_facts": [
            "Lane evaluation uses saved fixture data and deterministic interpretable signal families.",
            "Every signal family is compared against no-skill, market, and shrinkage baselines.",
        ],
        "inferred_patterns": [
            "No signal family beats the current-market baseline strongly enough for replay design.",
        ],
        "unknowns": [
            "Lane-level sample sizes remain too limited for confidence.",
            "Market baseline dominance may persist with larger data.",
        ],
        **LANE_EVALUATION_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_lane_evaluation_report(
    *,
    fixture_path: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    dataset = build_resolution_aware_dataset(fixture_path)
    payload = evaluate_lanes(dataset)
    payload["report_paths"] = _write_reports(payload, output_root=output_root)
    return payload


def _evaluate_lane(
    lane: dict[str, Any],
    *,
    features_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    lane_features = [
        features_by_id[market_id] for market_id in lane["market_ids"] if market_id in features_by_id
    ]
    resolved = [feature for feature in lane_features if feature["prediction_label"] is not None]
    baselines = _score_baselines(resolved)
    candidate_results = _score_signal_families(resolved, baselines=baselines)
    if lane["research_status"] == "REJECTED_BROAD_LANE":
        lane_status = "BROAD_LANE_REJECTED"
    elif lane["resolved_label_count"] < MIN_LANE_RESOLVED_OBSERVATIONS:
        lane_status = "LANE_TOO_THIN"
    elif any(result["credible_signal_family"] for result in candidate_results.values()):
        lane_status = "CANDIDATE_SIGNAL_DISCOVERED"
    else:
        lane_status = "BASELINES_NOT_BEATEN"
    return {
        "lane_id": lane["lane_id"],
        "rank": lane["rank"],
        "lane_status": lane_status,
        "sample_size": lane["sample_size"],
        "resolved_observation_count": len(resolved),
        "market_ids": lane["market_ids"],
        "baselines": baselines,
        "candidate_results": candidate_results,
        "confidence_warnings": _confidence_warnings(lane=lane, resolved=resolved),
        "observed_facts": [
            "Only resolved observations are scored.",
            "Unresolved and excluded markets are retained as diagnostics, not labels.",
        ],
        "inferred_patterns": [
            "Current-market probability remains the required benchmark for this lane.",
        ],
        "unknowns": [
            "Per-lane estimates are fragile until materially more resolved history exists.",
        ],
    }


def _score_baselines(resolved: list[dict[str, Any]]) -> dict[str, Any]:
    definitions = {
        "naive_50_50": ("naive_probability", "No-skill 50/50 probability baseline."),
        "current_market_probability": (
            "current_market_probability",
            "Latest saved market-implied probability baseline.",
        ),
        "simple_calibrated_heuristic": (
            "simple_calibrated_probability",
            "Transparent shrinkage heuristic toward 50/50.",
        ),
    }
    return {
        name: score_probability_forecast(
            resolved,
            probability_key=probability_key,
            description=description,
        )
        for name, (probability_key, description) in definitions.items()
    }


def _score_signal_families(
    resolved: list[dict[str, Any]],
    *,
    baselines: dict[str, Any],
) -> dict[str, Any]:
    results = {}
    current = baselines["current_market_probability"]
    for family in SIGNAL_FAMILIES:
        score = score_probability_forecast(
            resolved,
            probability_key=family["probability_key"],
            description=family["plain_english_explanation"],
        )
        comparisons = {
            baseline_name: _comparison(score, baseline)
            for baseline_name, baseline in baselines.items()
        }
        beats_current = comparisons["current_market_probability"]["beats_with_required_margin"]
        results[family["signal_family_id"]] = {
            **score,
            "signal_family_id": family["signal_family_id"],
            "baseline_brier_score": current["brier_score"],
            "baseline_comparisons": comparisons,
            "beats_current_market_probability": beats_current,
            "credible_signal_family": bool(
                beats_current
                and comparisons["naive_50_50"]["beats_with_required_margin"]
                and comparisons["simple_calibrated_heuristic"]["beats_with_required_margin"]
            ),
            "opaque_model": False,
        }
    return results


def _comparison(candidate: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    if candidate["brier_score"] is None or baseline["brier_score"] is None:
        return {
            "candidate_brier_score": candidate["brier_score"],
            "baseline_brier_score": baseline["brier_score"],
            "brier_improvement": None,
            "beats_with_required_margin": False,
        }
    improvement = round(float(baseline["brier_score"]) - float(candidate["brier_score"]), 6)
    return {
        "candidate_brier_score": candidate["brier_score"],
        "baseline_brier_score": baseline["brier_score"],
        "brier_improvement": improvement,
        "beats_with_required_margin": improvement >= SIGNAL_BRIER_MARGIN,
    }


def _confidence_warnings(*, lane: dict[str, Any], resolved: list[dict[str, Any]]) -> list[str]:
    warnings = []
    if len(resolved) < MIN_LANE_RESOLVED_OBSERVATIONS:
        warnings.append("LANE_TOO_THIN")
    if lane["research_status"] == "REJECTED_BROAD_LANE":
        warnings.append("BROAD_LANE_REJECTED")
    if len(resolved) < 20:
        warnings.append("RESOLVED_SAMPLE_BELOW_REPLAY_DESIGN_THRESHOLD")
    return warnings


def _write_reports(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    output = Path(output_root)
    lane_root = output / LANE_EVALUATION_ROOT
    candidate_root = output / PREDICTION_CANDIDATE_ROOT
    lane_root.mkdir(parents=True, exist_ok=True)
    candidate_root.mkdir(parents=True, exist_ok=True)
    lane_json = lane_root / "latest_lane_evaluation.json"
    lane_md = lane_root / "latest_lane_evaluation.md"
    candidate_json = candidate_root / "latest_prediction_candidates.json"
    candidate_md = candidate_root / "latest_prediction_candidates.md"
    for json_path in (lane_json, candidate_json):
        json_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
    markdown = _markdown(payload)
    lane_md.write_text(markdown, encoding="utf-8")
    candidate_md.write_text(markdown, encoding="utf-8")
    return {
        "json": str(lane_json),
        "markdown": str(lane_md),
        "prediction_candidates_json": str(candidate_json),
        "prediction_candidates_markdown": str(candidate_md),
    }


def _markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Sequence 23 Lane Evaluation",
        "",
        "Research-only lane evaluation report. No execution authority.",
        "",
        f"Status: {payload['lane_evaluation_status']}",
        f"Best lane: {payload['best_lane_evaluation']['lane_id']}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Observed facts",
    ]
    lines.extend(f"- {item}" for item in payload["observed_facts"])
    lines.extend(["", "## Inferred patterns"])
    lines.extend(f"- {item}" for item in payload["inferred_patterns"])
    lines.extend(["", "## Unknowns"])
    lines.extend(f"- {item}" for item in payload["unknowns"])
    return "\n".join(lines) + "\n"
