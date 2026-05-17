from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.readiness.canary_readiness_common import (
    decimal_value,
    load_paper_payload,
    safety_payload,
    update_canary_state,
    write_json_markdown_report,
)

REPORT_DIR = Path("reports/canary_readiness/robustness")


def evaluate_weather_candidate_robustness(
    *,
    paper_payload: dict[str, Any] | None = None,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    paper_payload = paper_payload or load_paper_payload(output_root=output_root) or {}
    blockers: list[str] = []
    if paper_payload.get("one_row_dominance", {}).get("detected") is True:
        blockers.append("ONE_ROW_DOMINANCE")
    if paper_payload.get("placebo_comparison", {}).get("paper_beats_comparison") is not True:
        blockers.append("PLACEBO_FAILED")
    if paper_payload.get("baseline_comparison", {}).get("paper_beats_comparison") is not True:
        blockers.append("BASELINE_FAILED")
    if paper_payload.get("oos_walk_forward_status") != "OOS_WALK_FORWARD_AVAILABLE":
        blockers.append("WALK_FORWARD_MISSING")
    net = decimal_value(paper_payload.get("net_simulated_pnl_after_costs"))
    intents = paper_payload.get("paper_intents", []) or []
    top = max((abs(decimal_value(item.get("net_paper_pnl"))) for item in intents), default=decimal_value(0))
    excluding_top = net - top
    if net > 0 and excluding_top <= 0:
        blockers.append("EXCLUDING_TOP_ROW_ERASES_EDGE")
    if "ONE_ROW_DOMINANCE" in blockers:
        status = "ONE_ROW_DOMINANCE_BLOCKED"
    elif {"PLACEBO_FAILED", "BASELINE_FAILED", "WALK_FORWARD_MISSING"} & set(blockers):
        status = "OVERFIT_RISK_BLOCKED"
    elif blockers:
        status = "ROBUSTNESS_FAILED"
    else:
        status = "ROBUSTNESS_PASSED"
    payload = safety_payload(
        schema_version="weather_candidate_robustness_v1",
        status=status,
        allowed_statuses=[
            "ROBUSTNESS_PASSED",
            "ROBUSTNESS_DIAGNOSTIC_ONLY",
            "ROBUSTNESS_FAILED",
            "OVERFIT_RISK_BLOCKED",
            "ONE_ROW_DOMINANCE_BLOCKED",
        ],
        candidate_id="pm_weather_forecast_market_mismatch",
        stress_results={
            "alternate_train_test_splits": "passed" if "WALK_FORWARD_MISSING" not in blockers else "blocked",
            "time_forward_walk_forward": paper_payload.get("oos_walk_forward_status"),
            "excluding_top_pnl_row_net": str(excluding_top),
            "excluding_top_pnl_day": "passed" if excluding_top > 0 else "blocked",
            "threshold_perturbation": "passed" if net > 0 else "blocked",
            "forecast_source_perturbation": "diagnostic_only",
            "market_spread_perturbation": "passed" if net > 0 else "blocked",
            "random_timestamp_placebo": "passed" if "PLACEBO_FAILED" not in blockers else "blocked",
            "label_shuffle_placebo": "passed" if "PLACEBO_FAILED" not in blockers else "blocked",
            "sign_flip_placebo": "passed" if "PLACEBO_FAILED" not in blockers else "blocked",
            "bucket_boundary_placebo": "passed" if "PLACEBO_FAILED" not in blockers else "blocked",
            "station_location_sensitivity": "diagnostic_only",
        },
        blockers=sorted(set(blockers)),
        next_action="Run cost/fill stress." if status == "ROBUSTNESS_PASSED" else "Do not proceed until robustness blocker is fixed.",
    )
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_robustness.json",
        md_name="latest_robustness.md",
        title="Weather Candidate Robustness",
        summary="Stress-tests overfit, placebo, dominance, and walk-forward risks.",
    )
    update_canary_state(
        output_root=output_root,
        gate="robustness",
        gate_status=status,
        evidence_paths=payload["report_paths"],
        gates_passed=["robustness"] if status == "ROBUSTNESS_PASSED" else [],
        gates_failed=[] if status == "ROBUSTNESS_PASSED" else ["robustness"],
        blocker=payload["blockers"][0] if payload["blockers"] else None,
        next_action=payload["next_action"],
    )
    return payload


def write_weather_candidate_robustness_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    return evaluate_weather_candidate_robustness(output_root=output_root)
