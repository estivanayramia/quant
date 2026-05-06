from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.data.prediction_markets.activity_capture import build_activity_dataset_from_capture
from quant_os.research.prediction_markets.oos_validation import evaluate_lane_oos_validation

REPORT_ROOT = Path("reports/sequence26/robustness")
ROBUSTNESS_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
}


def evaluate_lane_robustness(*, oos_validation: dict[str, Any]) -> dict[str, Any]:
    warnings = []
    if not oos_validation["candidate_signal_survives_oos"]:
        warnings.append("MARKET_BASELINE_NOT_BEATEN_OOS")
    if oos_validation["in_sample_only_signal_count"] > 0:
        warnings.append("IN_SAMPLE_ONLY_SIGNAL_DEGRADES_OOS")
    if oos_validation["oos_observation_count"] < 10:
        warnings.append("LANE_OOS_TOO_THIN")
    if not oos_validation["leakage_check"]["passed"]:
        warnings.extend(oos_validation["leakage_check"]["warnings"])
    status = (
        "OOS_SIGNAL_ROBUST_ENOUGH_FOR_REPLAY_DESIGN"
        if not warnings and oos_validation["candidate_signal_survives_oos"]
        else "OOS_SIGNAL_NOT_ROBUST"
    )
    return {
        "sequence": "26",
        "source": oos_validation["source"],
        "source_mode": oos_validation["source_mode"],
        "lane_id": oos_validation["lane_id"],
        "dataset_id": oos_validation["dataset_id"],
        "dataset_hash": oos_validation["dataset_hash"],
        "robustness_status": status,
        "warnings": _dedupe(warnings),
        "summary": {
            "resolved_observation_count": oos_validation["resolved_observation_count"],
            "oos_observation_count": oos_validation["oos_observation_count"],
            "candidate_signal_survives_oos": oos_validation["candidate_signal_survives_oos"],
            "market_baseline_dominant": oos_validation["market_baseline_dominant"],
            "in_sample_only_signal_count": oos_validation["in_sample_only_signal_count"],
        },
        "observed_facts": [
            "Robustness checks summarize OOS survival, leakage, and in-sample degradation.",
        ],
        "inferred_patterns": [
            "A signal family must survive OOS validation before replay design can be justified.",
        ],
        "unknowns": [
            "Robust OOS diagnostics are still not live or execution readiness.",
        ],
        **ROBUSTNESS_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_lane_robustness_report(
    *,
    fixture_path: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    dataset = build_activity_dataset_from_capture(fixture_path)
    validation = evaluate_lane_oos_validation(dataset)
    payload = evaluate_lane_robustness(oos_validation=validation)
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


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
    json_path = root / "latest_robustness.json"
    md_path = root / "latest_robustness.md"
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    lines = [
        "# Sequence 26 Lane Robustness",
        "",
        "Research-only robustness report. No execution authority.",
        "",
        f"Lane: {payload['lane_id']}",
        f"Robustness: {payload['robustness_status']}",
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
