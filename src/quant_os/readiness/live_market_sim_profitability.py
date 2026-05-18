from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.autonomy.live_market_sim_common import (
    load_json,
    load_state,
    sim_safety_payload,
    write_state,
)
from quant_os.readiness.canary_readiness_common import write_json_markdown_report

REPORT_DIR = Path("reports/live_market_sim_profitability/final")


def build_live_market_sim_profitability_readiness(
    *,
    output_root: str | Path = ".",
    state: dict[str, Any] | None = None,
    pnl: dict[str, Any] | None = None,
    comparison: dict[str, Any] | None = None,
    reconciliation: dict[str, Any] | None = None,
    min_observations: int = 10,
    min_intents: int = 3,
    min_fills: int = 1,
    min_resolved_outcomes: int = 3,
) -> dict[str, Any]:
    state = state or load_state(output_root=output_root)
    pnl = pnl or load_json("reports/live_market_sim_profitability/pnl/latest_pnl.json", output_root=output_root) or {}
    comparison = comparison or load_json(
        "reports/live_market_sim_profitability/comparison/latest_comparison.json",
        output_root=output_root,
    ) or {}
    reconciliation = reconciliation or load_json(
        "reports/live_market_sim_profitability/reconciliation/latest_reconciliation.json",
        output_root=output_root,
    ) or {}
    observation_count = len(state.get("observations", []) or [])
    intent_count = len(state.get("intents", []) or [])
    fill_count = len(state.get("fills", []) or [])
    resolved = int(pnl.get("resolved_outcome_count") or 0)
    pending = int(pnl.get("pending_outcome_count") or state.get("pending_outcome_count") or 0)
    net = float(pnl.get("fake_net_pnl") or 0.0)
    blockers: list[str] = []
    if observation_count < min_observations:
        blockers.append("MIN_OBSERVATIONS_NOT_MET")
    if intent_count < min_intents:
        blockers.append("MIN_ELIGIBLE_INTENTS_NOT_MET")
    if fill_count < min_fills:
        blockers.append("MIN_FAKE_FILLS_NOT_MET")
    if blockers:
        status = "LIVE_MARKET_SIMULATED_PROFITABILITY_NEEDS_MORE_OBSERVATIONS"
    elif pending or resolved < min_resolved_outcomes or reconciliation.get("status") == "LIVE_SIM_RECONCILIATION_PENDING_OUTCOMES":
        status = "LIVE_MARKET_SIMULATED_PROFITABILITY_PENDING_OUTCOMES"
        if resolved < min_resolved_outcomes:
            blockers.append("MIN_RESOLVED_OUTCOMES_NOT_MET")
    else:
        if net <= 0:
            blockers.append("FAKE_NET_PNL_NOT_POSITIVE")
        if comparison.get("status") != "LIVE_SIM_BASELINES_BEATEN":
            blockers.append("BASELINE_OR_PLACEBO_NOT_BEATEN")
        if reconciliation.get("status") != "LIVE_SIM_RECONCILIATION_PASSED":
            blockers.append("RECONCILIATION_NOT_PASSED")
        if blockers:
            status = "LIVE_MARKET_SIMULATED_PROFITABILITY_NOT_PROVEN"
        else:
            status = "LIVE_MARKET_SIMULATED_PROFITABILITY_PROVEN"
    return sim_safety_payload(
        schema_version="live_market_sim_profitability_readiness_v1",
        status=status,
        allowed_statuses=[
            "LIVE_MARKET_SIMULATED_PROFITABILITY_PROVEN",
            "LIVE_MARKET_SIMULATED_PROFITABILITY_PENDING_OUTCOMES",
            "LIVE_MARKET_SIMULATED_PROFITABILITY_NEEDS_MORE_OBSERVATIONS",
            "LIVE_MARKET_SIMULATED_PROFITABILITY_NOT_PROVEN",
            "LIVE_MARKET_SIMULATED_PROFITABILITY_BLOCKED",
        ],
        observation_count=observation_count,
        eligible_intent_count=intent_count,
        fake_fill_count=fill_count,
        resolved_outcome_count=resolved,
        pending_outcome_count=pending,
        fake_net_pnl=net,
        baseline_status=comparison.get("status"),
        reconciliation_status=reconciliation.get("status"),
        unsafe_action_attempts=0,
        auth_key_order_attempts=0,
        hidden_local_state_dependency=False,
        blockers=blockers,
        next_action="Run scheduler/resume loop for more observations or pending outcomes."
        if status != "LIVE_MARKET_SIMULATED_PROFITABILITY_PROVEN"
        else "Profitability proven in fake-money live-market simulation; live trading remains disabled.",
        exact_resume_command=state.get("exact_resume_command"),
    )


def write_live_market_sim_profitability_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_live_market_sim_profitability_readiness(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_live_market_sim_profitability.json",
        md_name="latest_live_market_sim_profitability.md",
        title="Live Market Simulated Profitability",
        summary="Final fake-money live-market simulated profitability readiness gate.",
    )
    write_state(output_root=output_root, current_blockers=payload["blockers"], next_action=payload["next_action"])
    return payload
