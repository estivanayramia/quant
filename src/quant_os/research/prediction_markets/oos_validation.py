from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.data.prediction_markets.activity_capture import build_activity_dataset_from_capture
from quant_os.research.prediction_markets.label_quality import evaluate_label_quality
from quant_os.research.prediction_markets.lane_dynamics import DYNAMIC_SIGNAL_FAMILIES
from quant_os.research.prediction_markets.lane_splits import (
    MIN_OOS_OBSERVATIONS,
    build_chronological_lane_splits,
)
from quant_os.research.prediction_markets.metrics import score_probability_forecast

REPORT_ROOT = Path("reports/sequence26/oos_validation")
OOS_VALIDATION_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
}
BASELINE_DEFINITIONS = {
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
SIGNAL_BRIER_MARGIN = 0.01


def evaluate_lane_oos_validation(dataset: dict[str, Any]) -> dict[str, Any]:
    splits = build_chronological_lane_splits(dataset)
    label_quality = evaluate_label_quality(dataset)
    train = splits["splits"]["train"]
    validation = splits["splits"]["validation"]
    test = splits["splits"]["test"]
    oos = [*validation, *test]
    baselines = {
        "train": _score_baselines(train),
        "validation": _score_baselines(validation),
        "test": _score_baselines(test),
        "oos": _score_baselines(oos),
    }
    candidate_results = _candidate_results(train=train, oos=oos, baselines=baselines)
    survives = any(result["survives_oos"] for result in candidate_results.values())
    in_sample_only_count = sum(
        1
        for result in candidate_results.values()
        if result["beats_market_in_sample"] and not result["survives_oos"]
    )
    market_baseline_dominant = not any(
        result["oos_baseline_comparisons"]["current_market_probability"][
            "beats_with_required_margin"
        ]
        for result in candidate_results.values()
    )
    status = _status(
        splits=splits,
        candidate_signal_survives_oos=survives,
        in_sample_only_signal_count=in_sample_only_count,
    )
    return {
        "sequence": "26",
        "source": dataset["source"],
        "source_mode": dataset["source_mode"],
        "lane_id": dataset["lane_id"],
        "dataset_id": dataset["dataset_id"],
        "dataset_hash": dataset["dataset_hash"],
        "oos_validation_status": status,
        "resolved_observation_count": splits["resolved_observation_count"],
        "oos_observation_count": splits["oos_observation_count"],
        "split_counts": splits["split_counts"],
        "leakage_check": splits["leakage_check"],
        "label_quality_status": label_quality["label_quality_status"],
        "label_quality_summary": label_quality["summary"],
        "baseline_names": list(BASELINE_DEFINITIONS),
        "baselines": baselines,
        "candidate_results": candidate_results,
        "candidate_signal_survives_oos": survives,
        "in_sample_only_signal_count": in_sample_only_count,
        "market_baseline_dominant": market_baseline_dominant,
        "confidence_warnings": _confidence_warnings(
            splits=splits,
            label_quality=label_quality,
            market_baseline_dominant=market_baseline_dominant,
        ),
        "observed_facts": [
            "Lane OOS validation uses chronological splits only.",
            "Every signal family is compared against no-skill, market, and shrinkage baselines.",
        ],
        "inferred_patterns": [
            "In-sample diagnostics are not sufficient; candidates must survive OOS comparison.",
        ],
        "unknowns": [
            "OOS validation is still a research gate, not a replay or execution system.",
        ],
        **OOS_VALIDATION_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_lane_oos_validation_report(
    *,
    fixture_path: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    dataset = build_activity_dataset_from_capture(fixture_path)
    payload = evaluate_lane_oos_validation(dataset)
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _score_baselines(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        name: score_probability_forecast(
            rows,
            probability_key=probability_key,
            description=description,
        )
        for name, (probability_key, description) in BASELINE_DEFINITIONS.items()
    }


def _candidate_results(
    *,
    train: list[dict[str, Any]],
    oos: list[dict[str, Any]],
    baselines: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    results = {}
    for family in DYNAMIC_SIGNAL_FAMILIES:
        train_score = score_probability_forecast(
            train,
            probability_key=family["probability_key"],
            description=family["plain_english_explanation"],
        )
        oos_score = score_probability_forecast(
            oos,
            probability_key=family["probability_key"],
            description=family["plain_english_explanation"],
        )
        train_comparisons = {
            name: _comparison(train_score, baseline)
            for name, baseline in baselines["train"].items()
        }
        oos_comparisons = {
            name: _comparison(oos_score, baseline) for name, baseline in baselines["oos"].items()
        }
        beats_in_sample = train_comparisons["current_market_probability"][
            "beats_with_required_margin"
        ]
        survives_oos = bool(
            len(oos) >= MIN_OOS_OBSERVATIONS
            and oos_comparisons["current_market_probability"]["beats_with_required_margin"]
            and oos_comparisons["naive_50_50"]["beats_with_required_margin"]
            and oos_comparisons["simple_calibrated_heuristic"]["beats_with_required_margin"]
        )
        results[family["signal_family_id"]] = {
            "signal_family_id": family["signal_family_id"],
            "name": family["name"],
            "plain_english_explanation": family["plain_english_explanation"],
            "feature_list": family["feature_list"],
            "why_it_might_work": family["why_it_might_work"],
            "why_it_might_fail": family["why_it_might_fail"],
            "failure_mode_notes": family["failure_mode_notes"],
            "train": train_score,
            "oos": oos_score,
            "train_baseline_comparisons": train_comparisons,
            "oos_baseline_comparisons": oos_comparisons,
            "beats_market_in_sample": beats_in_sample,
            "survives_oos": survives_oos,
            "credible_signal_family": survives_oos,
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


def _status(
    *,
    splits: dict[str, Any],
    candidate_signal_survives_oos: bool,
    in_sample_only_signal_count: int,
) -> str:
    if splits["split_status"] != "OOS_SPLITS_READY" or not splits["leakage_check"]["passed"]:
        return "LANE_OOS_TOO_THIN"
    if candidate_signal_survives_oos:
        return "CANDIDATE_SIGNAL_SURVIVES_OOS"
    if in_sample_only_signal_count:
        return "DIRECTIONAL_IMPROVEMENT_ONLY"
    return "BASELINES_NOT_BEATEN"


def _confidence_warnings(
    *,
    splits: dict[str, Any],
    label_quality: dict[str, Any],
    market_baseline_dominant: bool,
) -> list[str]:
    warnings = []
    if splits["split_status"] != "OOS_SPLITS_READY":
        warnings.append("LANE_OOS_TOO_THIN")
    warnings.extend(splits["leakage_check"]["warnings"])
    warnings.extend(label_quality["warnings"])
    if market_baseline_dominant:
        warnings.append("MARKET_BASELINE_NOT_BEATEN_OOS")
    return _dedupe(warnings)


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    deduped = []
    for item in items:
        if item not in seen:
            deduped.append(item)
            seen.add(item)
    return deduped


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_oos_validation.json"
    md_path = root / "latest_oos_validation.md"
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    lines = [
        "# Sequence 26 Lane OOS Validation",
        "",
        "Research-only lane OOS validation report. No execution authority.",
        "",
        f"Lane: {payload['lane_id']}",
        f"OOS status: {payload['oos_validation_status']}",
        f"Resolved observations: {payload['resolved_observation_count']}",
        f"OOS observations: {payload['oos_observation_count']}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Observed facts",
    ]
    lines.extend(f"- {item}" for item in payload["observed_facts"])
    lines.extend(["", "## Inferred patterns"])
    lines.extend(f"- {item}" for item in payload["inferred_patterns"])
    lines.extend(["", "## Unknowns"])
    lines.extend(f"- {item}" for item in payload["unknowns"])
    lines.extend(["", "## Confidence warnings"])
    lines.extend(f"- {item}" for item in (payload["confidence_warnings"] or ["None"]))
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
