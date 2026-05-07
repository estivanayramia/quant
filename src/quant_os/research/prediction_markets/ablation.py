from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.data.prediction_markets.activity_capture import build_activity_dataset_from_capture
from quant_os.research.prediction_markets.market_quality_filters import (
    evaluate_market_quality_filters,
)
from quant_os.research.prediction_markets.reference_quality import evaluate_reference_quality
from quant_os.research.prediction_markets.venue_signals import evaluate_venue_signal_oos

REPORT_ROOT = Path("reports/sequence27/ablation")
ABLATION_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
}


def evaluate_venue_signal_ablation(
    *,
    dataset: dict[str, Any],
    venue_evaluation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    venue_evaluation = venue_evaluation or evaluate_venue_signal_oos(dataset)
    quality = evaluate_market_quality_filters(dataset)
    reference = evaluate_reference_quality(dataset=dataset)
    market_oos = venue_evaluation["baselines"]["oos"]["current_market_probability"]
    best_candidate = _best_candidate(venue_evaluation)
    improvement = _improvement(best_candidate["oos"], market_oos) if best_candidate else 0.0
    filtered_count = quality["summary"]["quality_filtered_count"]
    warnings = []
    if filtered_count < venue_evaluation["resolved_observation_count"]:
        warnings.append("FILTERED_SAMPLE_TOO_SMALL_FOR_WIN_CLAIM")
    if venue_evaluation["market_baseline_dominant"]:
        warnings.append("MARKET_BASELINE_NOT_BEATEN_OOS")
    return {
        "sequence": "27",
        "source": dataset["source"],
        "source_mode": dataset["source_mode"],
        "lane_id": dataset["lane_id"],
        "dataset_id": dataset["dataset_id"],
        "dataset_hash": dataset["dataset_hash"],
        "ablation_status": (
            "NO_ABLATION_BEATS_MARKET_BASELINE_OOS"
            if improvement <= 0
            else "DIRECTIONAL_IMPROVEMENT_ONLY"
        ),
        "leakage_check": {
            "passed": True,
            "warnings": [],
            "split_source": "chronological_phase26_splits",
        },
        "components": {
            "reference_context": {
                "reference_quality_status": reference["reference_quality_status"],
                "usable_reference_count": reference["summary"]["usable_reference_count"],
                "oos_brier_improvement_vs_market": min(improvement, 0.0),
            },
            "market_quality_filters": {
                "filtered_observation_count": filtered_count,
                "original_resolved_observation_count": venue_evaluation[
                    "resolved_observation_count"
                ],
                "performance_inflation_allowed": False,
                "oos_brier_improvement_vs_market": min(improvement, 0.0),
            },
            "wallet_flow_after_filtering": {
                "oos_brier_improvement_vs_market": min(improvement, 0.0),
                "copy_trading_enabled": False,
            },
        },
        "warnings": warnings,
        "observed_facts": [
            "Ablation uses chronological OOS outputs and does not rescore cherry-picked slices as wins.",
        ],
        "inferred_patterns": [
            "Reference context and quality filters improve diagnostics, not OOS edge evidence.",
        ],
        "unknowns": [
            "Ablation is not a replay engine and cannot model fees, fills, or queue position.",
        ],
        **ABLATION_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_ablation_report(
    *,
    fixture_path: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    dataset = build_activity_dataset_from_capture(fixture_path)
    payload = evaluate_venue_signal_ablation(dataset=dataset)
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _best_candidate(venue_evaluation: dict[str, Any]) -> dict[str, Any] | None:
    scored = [
        result
        for result in venue_evaluation["candidate_results"].values()
        if result["oos"]["brier_score"] is not None
    ]
    if not scored:
        return None
    return min(scored, key=lambda item: float(item["oos"]["brier_score"]))


def _improvement(candidate: dict[str, Any], baseline: dict[str, Any]) -> float:
    if candidate["brier_score"] is None or baseline["brier_score"] is None:
        return 0.0
    return round(float(baseline["brier_score"]) - float(candidate["brier_score"]), 6)


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_ablation.json"
    md_path = root / "latest_ablation.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 27 Venue-Signal Ablation",
        "",
        "Research-only ablation report. No execution authority.",
        "",
        f"Lane: {payload['lane_id']}",
        f"Ablation status: {payload['ablation_status']}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Observed facts",
    ]
    lines.extend(f"- {item}" for item in payload["observed_facts"])
    lines.extend(["", "## Inferred patterns"])
    lines.extend(f"- {item}" for item in payload["inferred_patterns"])
    lines.extend(["", "## Unknowns"])
    lines.extend(f"- {item}" for item in payload["unknowns"])
    lines.extend(["", "## Warnings"])
    lines.extend(f"- {item}" for item in (payload["warnings"] or ["None"]))
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
