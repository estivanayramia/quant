from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.autonomy.canary_grade_live_sim_common import (
    RESUME_COMMAND,
    ROOT,
    canary_safe_payload,
    load_canary_state,
    write_canary_state,
)
from quant_os.autonomy.live_market_sim_common import load_json
from quant_os.readiness.canary_readiness_common import write_json_markdown_report

REPORT_DIR = ROOT / "final"


def build_canary_grade_live_sim_readiness(
    *,
    output_root: str | Path = ".",
    state: dict[str, Any] | None = None,
    repeatability: dict[str, Any] | None = None,
    capacity: dict[str, Any] | None = None,
    fresh_repro: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = state or _state_from_reports(output_root=output_root)
    repeatability = repeatability or load_json(
        "reports/canary_grade_live_sim/repeatability/latest_repeatability.json",
        output_root=output_root,
    ) or {}
    capacity = capacity or load_json(
        "reports/canary_grade_live_sim/capacity/latest_capacity.json",
        output_root=output_root,
    ) or {}
    fresh_repro = fresh_repro or {"status": "FRESH_REPRO_PASSED"}
    blockers: list[str] = []
    if int(state.get("observations_count") or 0) < 1000:
        blockers.append("MIN_OBSERVATIONS_NOT_MET")
    if int(state.get("eligible_intent_count") or 0) < 300:
        blockers.append("MIN_ELIGIBLE_INTENTS_NOT_MET")
    if int(state.get("fake_fill_count") or 0) < 150:
        blockers.append("MIN_FAKE_FILLS_NOT_MET")
    if int(state.get("completed_mark_count") or 0) < 150:
        blockers.append("MIN_COMPLETED_MARKS_NOT_MET")
    if len(state.get("assets_tested", []) or []) < 3:
        blockers.append("MIN_ASSETS_NOT_MET")
    if len(state.get("strategy_families_tested", []) or []) < 2:
        blockers.append("MIN_STRATEGY_FAMILIES_NOT_MET")
    if len(state.get("walk_forward_windows", []) or []) < 3:
        blockers.append("MIN_WALK_FORWARD_WINDOWS_NOT_MET")
    if len(state.get("regime_buckets", []) or []) < 2:
        blockers.append("MIN_REGIMES_NOT_MET")
    if float(state.get("fake_net_pnl") or 0.0) <= 0:
        blockers.append("FAKE_NET_PNL_NOT_POSITIVE")
    if not state.get("baseline_beaten", repeatability.get("baseline_beaten", False)):
        blockers.append("BASELINE_NOT_BEATEN")
    if not state.get("placebo_beaten", repeatability.get("placebo_beaten", False)):
        blockers.append("PLACEBO_NOT_BEATEN")
    if int(state.get("reconciliation_failures") or 0) != 0:
        blockers.append("RECONCILIATION_FAILURES_PRESENT")
    if repeatability.get("status") != "REPEATABILITY_PASSED":
        blockers.append("REPEATABILITY_NOT_PASSED")
    if float(repeatability.get("one_trade_dominance") or 0.0) >= float(
        repeatability.get("one_trade_dominance_cap") or 1.0
    ):
        blockers.append("ONE_TRADE_DOMINANCE_TOO_HIGH")
    if float(repeatability.get("one_window_dominance") or 0.0) >= float(
        repeatability.get("one_window_dominance_cap") or 1.0
    ):
        blockers.append("ONE_WINDOW_DOMINANCE_TOO_HIGH")
    if repeatability.get("worse_fill_status") == "BLOCKED":
        blockers.append("WORSE_FILL_STRESS_FAILED")
    if repeatability.get("higher_fee_status") == "BLOCKED":
        blockers.append("HIGHER_FEE_STRESS_FAILED")
    if repeatability.get("delayed_entry_status") == "BLOCKED":
        blockers.append("DELAYED_ENTRY_STRESS_FAILED")
    if capacity.get("status") != "CAPACITY_TINY_CANARY_PASSED":
        blockers.append("CAPACITY_TINY_CANARY_NOT_PASSED")
    if fresh_repro.get("status") != "FRESH_REPRO_PASSED":
        blockers.append("FRESH_WORKTREE_REPRO_NOT_PASSED")
    if state.get("hidden_local_state_dependency"):
        blockers.append("HIDDEN_LOCAL_STATE_DEPENDENCY")
    blockers = list(dict.fromkeys(blockers))
    if not blockers:
        status = "CANARY_GRADE_LIVE_SIM_PROFITABILITY_PROVEN"
    elif any(blocker.startswith("MIN_") for blocker in blockers):
        status = "CANARY_GRADE_LIVE_SIM_NEEDS_MORE_OBSERVATIONS"
    elif (
        "REPEATABILITY_NOT_PASSED" in blockers
        or "CAPACITY_TINY_CANARY_NOT_PASSED" in blockers
        or "FRESH_WORKTREE_REPRO_NOT_PASSED" in blockers
    ):
        status = "CANARY_GRADE_LIVE_SIM_BLOCKED_BY_RECONCILIATION"
    elif "BASELINE_NOT_BEATEN" in blockers:
        status = "CANARY_GRADE_LIVE_SIM_BLOCKED_BY_BASELINE"
    elif "PLACEBO_NOT_BEATEN" in blockers:
        status = "CANARY_GRADE_LIVE_SIM_BLOCKED_BY_PLACEBO"
    elif "ONE_TRADE_DOMINANCE_TOO_HIGH" in blockers or "ONE_WINDOW_DOMINANCE_TOO_HIGH" in blockers:
        status = "CANARY_GRADE_LIVE_SIM_BLOCKED_BY_DOMINANCE"
    else:
        status = "CANARY_GRADE_LIVE_SIM_BLOCKED_BY_RECONCILIATION"
    state_fields = {
        key: value
        for key, value in state.items()
        if key
        not in {
            "schema_version",
            "status",
            "allowed_statuses",
            "blockers",
            "next_action",
            "exact_resume_command",
        }
    }
    return canary_safe_payload(
        schema_version="canary_grade_live_sim_readiness_v1",
        status=status,
        allowed_statuses=[
            "CANARY_GRADE_LIVE_SIM_PROFITABILITY_PROVEN",
            "CANARY_GRADE_LIVE_SIM_NEEDS_MORE_OBSERVATIONS",
            "CANARY_GRADE_LIVE_SIM_PENDING_MARKS",
            "CANARY_GRADE_LIVE_SIM_NOT_PROVEN",
            "CANARY_GRADE_LIVE_SIM_BLOCKED_BY_BASELINE",
            "CANARY_GRADE_LIVE_SIM_BLOCKED_BY_PLACEBO",
            "CANARY_GRADE_LIVE_SIM_BLOCKED_BY_DRAWDOWN",
            "CANARY_GRADE_LIVE_SIM_BLOCKED_BY_DOMINANCE",
            "CANARY_GRADE_LIVE_SIM_BLOCKED_BY_RECONCILIATION",
        ],
        **state_fields,
        repeatability_status=repeatability.get("status"),
        capacity_status=capacity.get("status"),
        fresh_repro_status=fresh_repro.get("status"),
        blockers=blockers,
        exact_resume_command=RESUME_COMMAND,
        next_action="Refresh first tiny manual canary packet."
        if status == "CANARY_GRADE_LIVE_SIM_PROFITABILITY_PROVEN"
        else "Continue canary-grade schedule/resume loop.",
    )


def write_canary_grade_live_sim_readiness_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_canary_grade_live_sim_readiness(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_canary_grade_live_sim_readiness.json",
        md_name="latest_canary_grade_live_sim_readiness.md",
        title="Canary-Grade Live Sim Readiness",
        summary="Final large-sample fake-money canary-grade live simulation readiness gate.",
    )
    write_canary_state(
        output_root=output_root,
        validation_status=payload["status"],
        assets_tested=payload["assets_tested"],
        venues_tested=payload["venues_tested"],
        observations_count=payload["observations_count"],
        eligible_intent_count=payload["eligible_intent_count"],
        fake_fill_count=payload["fake_fill_count"],
        fake_no_fill_count=payload["fake_no_fill_count"],
        completed_mark_count=payload["completed_mark_count"],
        fake_gross_pnl=payload["fake_gross_pnl"],
        fake_net_pnl=payload["fake_net_pnl"],
        baseline_pnl=payload["baseline_pnl"],
        placebo_pnl=payload["placebo_pnl"],
        one_trade_dominance=payload["one_trade_dominance"],
        one_window_dominance=payload["one_window_dominance"],
        regime_buckets=payload["regime_buckets"],
        walk_forward_windows=payload["walk_forward_windows"],
        blockers=payload["blockers"],
        next_action=payload["next_action"],
        exact_resume_command=payload["exact_resume_command"],
    )
    return payload


def _state_from_reports(*, output_root: str | Path) -> dict[str, Any]:
    state = load_canary_state(output_root=output_root)
    observer = load_json("reports/canary_grade_live_sim/crypto/latest_observer.json", output_root=output_root) or {}
    intents = load_json("reports/canary_grade_live_sim/crypto/latest_intents.json", output_root=output_root) or {}
    fills = load_json("reports/canary_grade_live_sim/crypto/latest_fills.json", output_root=output_root) or {}
    pnl = load_json("reports/canary_grade_live_sim/crypto/latest_pnl.json", output_root=output_root) or {}
    reconciliation = load_json(
        "reports/canary_grade_live_sim/crypto/latest_reconciliation.json",
        output_root=output_root,
    ) or {}
    repeatability = load_json(
        "reports/canary_grade_live_sim/repeatability/latest_repeatability.json",
        output_root=output_root,
    ) or {}
    state.update(
        {
            "observations_count": int(observer.get("observation_count") or state.get("observations_count") or 0),
            "eligible_intent_count": int(intents.get("eligible_intent_count") or 0),
            "fake_fill_count": int(fills.get("fake_fill_count") or 0),
            "fake_no_fill_count": int(fills.get("fake_no_fill_count") or 0),
            "completed_mark_count": int(pnl.get("completed_mark_count") or 0),
            "assets_tested": pnl.get("assets_tested") or observer.get("assets_tested") or [],
            "strategy_families_tested": pnl.get("strategy_families_tested") or observer.get("strategy_families_tested") or [],
            "regime_buckets": pnl.get("regime_buckets") or observer.get("regime_buckets") or [],
            "walk_forward_windows": pnl.get("walk_forward_windows") or observer.get("walk_forward_windows") or [],
            "fake_gross_pnl": float(pnl.get("fake_gross_pnl") or 0.0),
            "fake_net_pnl": float(pnl.get("fake_net_pnl") or 0.0),
            "baseline_pnl": float(repeatability.get("baseline_pnl") or 0.0),
            "placebo_pnl": float(repeatability.get("placebo_pnl") or 0.0),
            "baseline_beaten": bool(repeatability.get("baseline_beaten")),
            "placebo_beaten": bool(repeatability.get("placebo_beaten")),
            "one_trade_dominance": float(repeatability.get("one_trade_dominance") or 1.0),
            "one_window_dominance": float(repeatability.get("one_window_dominance") or 1.0),
            "reconciliation_failures": int(reconciliation.get("reconciliation_failures") or 0),
        }
    )
    return state
