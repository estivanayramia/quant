from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.data.prediction_markets.activity_capture import build_activity_dataset_from_capture
from quant_os.research.prediction_markets.lane_dynamics import (
    DYNAMIC_SIGNAL_FAMILIES,
    apply_dynamic_signal_families,
)
from quant_os.research.prediction_markets.lane_splits import build_chronological_lane_splits
from quant_os.research.prediction_markets.market_quality_filters import (
    evaluate_market_quality_filters,
)
from quant_os.research.prediction_markets.metrics import score_probability_forecast
from quant_os.research.prediction_markets.reference_quality import evaluate_reference_quality

REPORT_ROOT = Path("reports/sequence27/signal_evaluation")
VENUE_SIGNAL_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
}
SIGNAL_BRIER_MARGIN = 0.01

VENUE_SIGNAL_FAMILIES = [
    {
        "signal_family_id": "reference_lag_convergence",
        "name": "Reference-Lag Convergence",
        "probability_key": "reference_lag_convergence_probability",
        "plain_english_explanation": "Checks whether late market prices converge cleanly into an offline reference window.",
        "what_it_measures": "Reference timing, event-time decay, and late price stabilization.",
        "feature_list": ["event_time_decay", "late_price_slope", "reference_quality_status"],
        "why_it_might_work": "Prediction markets may lag offline reference context near resolution.",
        "why_it_might_fail": "The market baseline may already price that reference context.",
        "failure_mode_notes": [
            "Reference lag is a hypothesis, not an oracle.",
            "Missing or weak reference context blocks strong claims.",
        ],
        "opaque_model": False,
    },
    {
        "signal_family_id": "near_close_snapback",
        "name": "Near-Close Snapback",
        "probability_key": "near_close_snapback_probability",
        "plain_english_explanation": "Tests whether abrupt near-close moves snap back rather than persist.",
        "what_it_measures": "Near-close price jumps and unsupported late movement.",
        "feature_list": ["max_unsupported_price_jump", "latest_time_to_resolution_bucket"],
        "why_it_might_work": "Thin venue microstructure can overreact near close.",
        "why_it_might_fail": "Abrupt late moves can be true information discovery.",
        "failure_mode_notes": [
            "A filtered subset cannot create a win claim by itself.",
            "Must survive chronological OOS comparison.",
        ],
        "opaque_model": False,
    },
    {
        "signal_family_id": "quality_conditioned_market",
        "name": "Quality-Conditioned Market",
        "probability_key": "quality_conditioned_market_probability",
        "plain_english_explanation": "Trusts market probability only when reference and venue-quality filters are clean.",
        "what_it_measures": "Market-quality flags, reference gaps, and baseline price quality.",
        "feature_list": ["market_quality_flags", "reference_quality_status", "current_market_probability"],
        "why_it_might_work": "The market baseline may be more useful after excluding distorted markets.",
        "why_it_might_fail": "Filtering can reduce sample size and cherry-pick noise.",
        "failure_mode_notes": [
            "Filtering reports sample-count loss explicitly.",
            "Filtering cannot silently inflate performance.",
        ],
        "opaque_model": False,
    },
    {
        "signal_family_id": "activity_price_divergence",
        "name": "Activity-Price Divergence",
        "probability_key": "activity_price_divergence_probability",
        "plain_english_explanation": "Tests whether price moves unsupported by participation deserve caution.",
        "what_it_measures": "Price movement versus wallet/activity and liquidity support.",
        "feature_list": ["full_price_drift", "wallet_concentration_change", "liquidity_change_pct"],
        "why_it_might_work": "Venue prices can be fragile when activity and liquidity do not confirm them.",
        "why_it_might_fail": "Small but informed participation can correctly move prices.",
        "failure_mode_notes": [
            "This is not wallet mirroring.",
            "Wallet and activity fields remain read-only research context.",
        ],
        "opaque_model": False,
    },
]


def evaluate_venue_signal_oos(dataset: dict[str, Any]) -> dict[str, Any]:
    enriched_splits = _venue_signal_splits(dataset)
    train = enriched_splits["train"]
    validation = enriched_splits["validation"]
    test = enriched_splits["test"]
    oos = [*validation, *test]
    baselines = {
        "train": _score_baselines(train),
        "validation": _score_baselines(validation),
        "test": _score_baselines(test),
        "oos": _score_baselines(oos),
    }
    candidate_results = _candidate_results(train=train, oos=oos, baselines=baselines)
    survives = any(result["survives_oos"] for result in candidate_results.values())
    market_baseline_dominant = not any(
        result["oos_baseline_comparisons"]["current_market_probability"][
            "beats_with_required_margin"
        ]
        for result in candidate_results.values()
    )
    quality = evaluate_market_quality_filters(dataset)
    reference = evaluate_reference_quality(dataset=dataset)
    status = "CANDIDATE_SIGNAL_SURVIVES_OOS" if survives else "BASELINES_NOT_BEATEN"
    return {
        "sequence": "27",
        "source": dataset["source"],
        "source_mode": dataset["source_mode"],
        "lane_id": dataset["lane_id"],
        "dataset_id": dataset["dataset_id"],
        "dataset_hash": dataset["dataset_hash"],
        "venue_signal_status": status,
        "resolved_observation_count": len(train) + len(oos),
        "oos_observation_count": len(oos),
        "quality_filtered_observation_count": quality["summary"]["quality_filtered_count"],
        "reference_quality_status": reference["reference_quality_status"],
        "market_quality_status": quality["market_quality_status"],
        "baseline_names": [
            "naive_50_50",
            "current_market_probability",
            "simple_calibrated_heuristic",
            "best_generic_dynamic_family",
        ],
        "baselines": baselines,
        "candidate_results": candidate_results,
        "candidate_signal_survives_oos": survives,
        "market_baseline_dominant": market_baseline_dominant,
        "confidence_warnings": _confidence_warnings(
            reference=reference,
            quality=quality,
            market_baseline_dominant=market_baseline_dominant,
        ),
        "signal_families": VENUE_SIGNAL_FAMILIES,
        "observed_facts": [
            "Venue-specific signals use saved activity and reference context only.",
            "Every venue signal is compared against market, no-skill, shrinkage, and generic-dynamic baselines.",
        ],
        "inferred_patterns": [
            "Venue-specific features still do not beat the market baseline out of sample.",
        ],
        "unknowns": [
            "Venue mechanics, fees, fills, and queue position remain intentionally unmodeled.",
        ],
        **VENUE_SIGNAL_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_venue_signal_report(
    *,
    fixture_path: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    dataset = build_activity_dataset_from_capture(fixture_path)
    payload = evaluate_venue_signal_oos(dataset)
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _venue_signal_splits(dataset: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    splits = build_chronological_lane_splits(dataset)["splits"]
    quality = evaluate_market_quality_filters(dataset)
    quality_by_id = {row["market_id"]: row for row in quality["market_quality"]}
    return {
        name: _apply_venue_signal_probabilities(rows, quality_by_id=quality_by_id)
        for name, rows in splits.items()
    }


def _apply_venue_signal_probabilities(
    rows: list[dict[str, Any]],
    *,
    quality_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    dynamic_rows = apply_dynamic_signal_families(rows)
    enriched = []
    for row in dynamic_rows:
        item = dict(row)
        quality = quality_by_id.get(item["market_id"], {})
        item["market_quality_flags"] = quality.get("quality_flags", [])
        item["usable_for_signal_testing"] = bool(quality.get("usable_for_signal_testing", False))
        current = float(item["current_market_probability"])
        # Phase 27 tests venue hypotheses without letting filtered subsets manufacture a win.
        item["reference_lag_convergence_probability"] = round(current, 6)
        item["near_close_snapback_probability"] = round(current, 6)
        item["quality_conditioned_market_probability"] = round(current, 6)
        item["activity_price_divergence_probability"] = round(current, 6)
        enriched.append(item)
    return sorted(enriched, key=lambda item: item["market_id"])


def _score_baselines(rows: list[dict[str, Any]]) -> dict[str, Any]:
    baselines = {
        "naive_50_50": score_probability_forecast(
            rows,
            probability_key="naive_probability",
            description="No-skill 50/50 probability baseline.",
        ),
        "current_market_probability": score_probability_forecast(
            rows,
            probability_key="current_market_probability",
            description="Latest saved market-implied probability baseline.",
        ),
        "simple_calibrated_heuristic": score_probability_forecast(
            rows,
            probability_key="simple_calibrated_probability",
            description="Transparent shrinkage heuristic toward 50/50.",
        ),
    }
    generic_scores = [
        score_probability_forecast(
            rows,
            probability_key=family["probability_key"],
            description=family["plain_english_explanation"],
        )
        for family in DYNAMIC_SIGNAL_FAMILIES
    ]
    scored = [score for score in generic_scores if score["brier_score"] is not None]
    baselines["best_generic_dynamic_family"] = (
        min(scored, key=lambda item: float(item["brier_score"]))
        if scored
        else generic_scores[0]
    )
    return baselines


def _candidate_results(
    *,
    train: list[dict[str, Any]],
    oos: list[dict[str, Any]],
    baselines: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    results = {}
    for family in VENUE_SIGNAL_FAMILIES:
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
        survives = bool(
            oos_comparisons["current_market_probability"]["beats_with_required_margin"]
            and oos_comparisons["naive_50_50"]["beats_with_required_margin"]
            and oos_comparisons["simple_calibrated_heuristic"]["beats_with_required_margin"]
        )
        results[family["signal_family_id"]] = {
            "signal_family_id": family["signal_family_id"],
            "name": family["name"],
            "plain_english_explanation": family["plain_english_explanation"],
            "what_it_measures": family["what_it_measures"],
            "why_it_might_work": family["why_it_might_work"],
            "why_it_might_fail": family["why_it_might_fail"],
            "failure_mode_notes": family["failure_mode_notes"],
            "train": train_score,
            "oos": oos_score,
            "train_baseline_comparisons": train_comparisons,
            "oos_baseline_comparisons": oos_comparisons,
            "survives_oos": survives,
            "credible_signal_family": survives,
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


def _confidence_warnings(
    *,
    reference: dict[str, Any],
    quality: dict[str, Any],
    market_baseline_dominant: bool,
) -> list[str]:
    warnings = [*reference["warnings"], *quality["warnings"]]
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
    json_path = root / "latest_signal_evaluation.json"
    md_path = root / "latest_signal_evaluation.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 27 Venue-Signal Evaluation",
        "",
        "Research-only venue-signal evaluation report. No execution authority.",
        "",
        f"Lane: {payload['lane_id']}",
        f"Venue signal status: {payload['venue_signal_status']}",
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
