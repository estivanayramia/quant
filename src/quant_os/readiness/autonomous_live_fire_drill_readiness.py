from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.readiness.canary_readiness_common import (
    load_gate_payload,
    safety_payload,
    write_json_markdown_report,
)

REPORT_DIR = Path("reports/autonomous_live_fire_drill/final")

SUCCESS = "AUTONOMOUS_LIVE_FIRE_DRILL_READY_AWAITING_HUMAN_CREDENTIALS_AND_ARMING"

REQUIRED = {
    "PAPER_CANDIDATE_MISSING": (
        "reports/profit_campaign/latest_profit_campaign.json",
        {"PAPER_PROFIT_CANDIDATE_FOUND", "PROFIT_CANDIDATE_ARTIFACTS_REGENERATED"},
    ),
    "FIRST_DOLLAR_PREFLIGHT_MISSING": (
        "reports/first_dollar_preflight/final/latest_first_dollar_preflight.json",
        {"FIRST_DOLLAR_PREFLIGHT_READY", "FIRST_DOLLAR_PREFLIGHT_STRUCTURALLY_READY_NO_CURRENT_MARKET"},
    ),
    "LIVE_MARKET_PAPER_REHEARSAL_MISSING": (
        "reports/live_market_paper_rehearsal/final/latest_live_market_paper_rehearsal.json",
        {"LIVE_MARKET_PAPER_REHEARSAL_PASSED"},
    ),
    "WATCHER_NOT_READY": (
        "reports/autonomous_live_fire_drill/watcher/latest_watcher.json",
        {"AUTONOMOUS_WATCHER_READY", "AUTONOMOUS_WATCHER_NO_ELIGIBLE_MARKET"},
    ),
    "DECISION_ENGINE_NOT_READY": (
        "reports/autonomous_live_fire_drill/decision/latest_decision.json",
        {"AUTONOMOUS_DECISION_READY", "AUTONOMOUS_DECISION_NO_TRADE"},
    ),
    "NO_TRANSMIT_INTENT_NOT_READY": (
        "reports/autonomous_live_fire_drill/no_transmit_intent/latest_intent.json",
        {"NO_TRANSMIT_INTENT_READY", "NO_TRANSMIT_INTENT_NO_TRADE"},
    ),
    "MOCK_LIFECYCLE_NOT_PASSED": (
        "reports/autonomous_live_fire_drill/mock_lifecycle/latest_mock_lifecycle.json",
        {"MOCK_ORDER_LIFECYCLE_PASSED"},
    ),
    "FAKE_EXECUTION_NOT_PASSED": (
        "reports/autonomous_live_fire_drill/fake_execution/latest_fake_execution.json",
        {"FAKE_EXECUTION_PASSED", "FAKE_EXECUTION_NO_TRADE"},
    ),
    "RISK_NOT_PASSED": (
        "reports/autonomous_live_fire_drill/risk/latest_risk.json",
        {"FIRE_DRILL_RISK_PASSED"},
    ),
    "RECONCILIATION_NOT_PASSED": (
        "reports/autonomous_live_fire_drill/reconciliation/latest_reconciliation.json",
        {"FAKE_RECONCILIATION_PASSED"},
    ),
    "POST_TRADE_REPORT_MISSING": (
        "reports/autonomous_live_fire_drill/post_trade/latest_post_trade_report.json",
        {"POST_TRADE_REPORT_READY"},
    ),
    "SCENARIOS_NOT_PASSED": (
        "reports/autonomous_live_fire_drill/scenarios/latest_scenarios.json",
        {"FIRE_DRILL_SCENARIOS_PASSED"},
    ),
    "SCHEDULER_PLAN_MISSING": (
        "reports/live_market_paper_rehearsal/schedule/latest_schedule.json",
        {"LIVE_MARKET_PAPER_REHEARSAL_SCHEDULE_READY"},
    ),
}


def build_fire_drill_readiness(*, output_root: str | Path = ".") -> dict[str, Any]:
    blockers = []
    gate_statuses = {}
    for blocker, (path, allowed) in REQUIRED.items():
        payload = load_gate_payload(path, output_root=output_root) or {}
        actual_status = _actual_status(payload)
        gate_statuses[path] = actual_status
        if actual_status not in allowed:
            blockers.append(blocker)
    risk = load_gate_payload(
        "reports/autonomous_live_fire_drill/risk/latest_risk.json",
        output_root=output_root,
    ) or {}
    if risk and risk.get("kill_switch_status") != "FIRE_DRILL_KILL_SWITCH_PASSED":
        blockers.append("KILL_SWITCH_NOT_PASSED")
    status = SUCCESS if not blockers else _blocked_status(blockers)
    return safety_payload(
        schema_version="autonomous_live_fire_drill_readiness_v1",
        status=status,
        allowed_statuses=[
            SUCCESS,
            "AUTONOMOUS_LIVE_FIRE_DRILL_CHECKPOINTED_NOT_COMPLETE",
            "FIRE_DRILL_BLOCKED_BY_AUDIT",
            "FIRE_DRILL_BLOCKED_BY_SCENARIOS",
            "FIRE_DRILL_BLOCKED_BY_RECONCILIATION",
            "FIRE_DRILL_BLOCKED_BY_RISK",
            "FIRE_DRILL_BLOCKED_BY_SECURITY",
            "HUMAN_CREDENTIALS_REQUIRED_BOUNDARY_REACHED",
        ],
        gate_statuses=gate_statuses,
        blockers=list(dict.fromkeys(blockers)),
        no_executable_real_order_path_exists=True,
        next_missing_thing="human_credentials_account_authority_legal_approval_and_arming"
        if status == SUCCESS
        else "deterministic_fire_drill_gate",
        request_signing_enabled=False,
        api_keys_loaded=False,
        private_keys_loaded=False,
        actual_order_count=0,
        actual_cancel_count=0,
        next_action="Prepare human boundary packet." if status == SUCCESS else "Run missing deterministic gates.",
    )


def write_fire_drill_readiness_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_fire_drill_readiness(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_fire_drill_readiness.json",
        md_name="latest_fire_drill_readiness.md",
        title="Autonomous Live Fire-Drill Readiness",
        summary="Final fake-money readiness gate. This is not authorization to trade.",
    )
    return payload


def _blocked_status(blockers: list[str]) -> str:
    if any("SCENARIOS" in blocker for blocker in blockers):
        return "FIRE_DRILL_BLOCKED_BY_SCENARIOS"
    if any("RECONCILIATION" in blocker for blocker in blockers):
        return "FIRE_DRILL_BLOCKED_BY_RECONCILIATION"
    if any("RISK" in blocker or "KILL_SWITCH" in blocker for blocker in blockers):
        return "FIRE_DRILL_BLOCKED_BY_RISK"
    return "FIRE_DRILL_BLOCKED_BY_AUDIT"


def _actual_status(payload: dict[str, Any]) -> str | None:
    return (
        payload.get("status")
        or payload.get("campaign_status")
        or payload.get("paper_profit_status")
        or payload.get("readiness_status")
    )
