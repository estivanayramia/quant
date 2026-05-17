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

REPORT_DIR = Path("reports/canary_readiness/cost_fill_stress")


def evaluate_cost_fill_stress(
    *,
    paper_payload: dict[str, Any] | None = None,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    paper_payload = paper_payload or load_paper_payload(output_root=output_root) or {}
    net = decimal_value(paper_payload.get("net_simulated_pnl_after_costs"))
    trades = decimal_value(paper_payload.get("trade_count") or len(paper_payload.get("paper_intents", []) or []))
    worse_1c = net - trades * decimal_value("0.01")
    worse_2c = net - trades * decimal_value("0.02")
    worse_3c = net - trades * decimal_value("0.03")
    worse_5c = net - trades * decimal_value("0.05")
    blockers: list[str] = []
    if worse_5c <= 0:
        blockers.append("WORSE_ENTRY_5C_ERASES_EDGE")
    fill_model = paper_payload.get("fill_model", {})
    if decimal_value(fill_model.get("partial_fill_fraction", 0)) <= 0:
        blockers.append("FILL_MODEL_TOO_UNCERTAIN")
    if decimal_value(fill_model.get("partial_fill_liquidity", 0)) <= 0:
        blockers.append("LIQUIDITY_TOO_THIN")
    if "WORSE_ENTRY_5C_ERASES_EDGE" in blockers:
        status = "COSTS_ERASE_EDGE"
    elif "LIQUIDITY_TOO_THIN" in blockers:
        status = "LIQUIDITY_TOO_THIN"
    elif "FILL_MODEL_TOO_UNCERTAIN" in blockers:
        status = "FILL_MODEL_TOO_UNCERTAIN"
    else:
        status = "COST_FILL_STRESS_PASSED"
    payload = safety_payload(
        schema_version="weather_candidate_cost_fill_stress_v1",
        status=status,
        allowed_statuses=[
            "COST_FILL_STRESS_PASSED",
            "COST_FILL_DIAGNOSTIC_ONLY",
            "COST_FILL_BLOCKED",
            "LIQUIDITY_TOO_THIN",
            "COSTS_ERASE_EDGE",
            "FILL_MODEL_TOO_UNCERTAIN",
        ],
        candidate_id="pm_weather_forecast_market_mismatch",
        stress_results={
            "bid_ask_spread": paper_payload.get("cost_model", {}).get("spread_bps"),
            "worse_entry_1c_net": str(worse_1c),
            "worse_entry_2c_net": str(worse_2c),
            "worse_entry_3c_net": str(worse_3c),
            "worse_entry_5c_net": str(worse_5c),
            "no_fill_on_thin_books": "enforced",
            "partial_fill": paper_payload.get("fill_model", {}).get("partial_fill_fraction"),
            "max_size_cap": 1,
            "minimum_book_depth": paper_payload.get("fill_model", {}).get("partial_fill_liquidity"),
            "adverse_selection": paper_payload.get("cost_model", {}).get("adverse_selection_bps"),
            "settlement_fee_assumptions": "paper conservative cost model",
            "latency_between_signal_and_decision": "diagnostic_only",
            "closing_exit_assumptions": "settlement-only binary contract",
        },
        blockers=sorted(set(blockers)),
        next_action="Run bounded shadow rehearsal." if status == "COST_FILL_STRESS_PASSED" else "Do not proceed until cost/fill blocker is fixed.",
    )
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_cost_fill_stress.json",
        md_name="latest_cost_fill_stress.md",
        title="Weather Candidate Cost Fill Stress",
        summary="Stresses fills, spread, liquidity, adverse selection, and latency assumptions.",
    )
    update_canary_state(
        output_root=output_root,
        gate="cost_fill_stress",
        gate_status=status,
        evidence_paths=payload["report_paths"],
        gates_passed=["cost_fill_stress"] if status == "COST_FILL_STRESS_PASSED" else [],
        gates_failed=[] if status == "COST_FILL_STRESS_PASSED" else ["cost_fill_stress"],
        blocker=payload["blockers"][0] if payload["blockers"] else None,
        next_action=payload["next_action"],
    )
    return payload


def write_weather_candidate_cost_fill_stress_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    return evaluate_cost_fill_stress(output_root=output_root)
