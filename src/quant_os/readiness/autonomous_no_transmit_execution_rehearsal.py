from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.autonomy.live_market_sim_common import load_json
from quant_os.readiness.canary_readiness_common import (
    safety_payload,
    write_json_markdown_report,
)

REPORT_DIR = Path("reports/autonomous_live_fire_drill/no_transmit_execution_rehearsal")
SUCCESS = "AUTONOMOUS_NO_TRANSMIT_EXECUTION_REHEARSAL_PASSED"

REPORTS = {
    "fire_drill": "reports/autonomous_live_fire_drill/final/latest_fire_drill_readiness.json",
    "watcher": "reports/autonomous_live_fire_drill/watcher/latest_watcher.json",
    "decision": "reports/autonomous_live_fire_drill/decision/latest_decision.json",
    "intent": "reports/autonomous_live_fire_drill/no_transmit_intent/latest_intent.json",
    "mock_lifecycle": "reports/autonomous_live_fire_drill/mock_lifecycle/latest_mock_lifecycle.json",
    "fake_execution": "reports/autonomous_live_fire_drill/fake_execution/latest_fake_execution.json",
    "post_trade": "reports/autonomous_live_fire_drill/post_trade/latest_post_trade_report.json",
    "risk": "reports/autonomous_live_fire_drill/risk/latest_risk.json",
    "reconciliation": "reports/autonomous_live_fire_drill/reconciliation/latest_reconciliation.json",
    "scenarios": "reports/autonomous_live_fire_drill/scenarios/latest_scenarios.json",
}


def build_autonomous_no_transmit_execution_rehearsal(
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    reports = {
        name: load_json(path, output_root=output_root) or {} for name, path in REPORTS.items()
    }
    gate_statuses = {name: payload.get("status") for name, payload in reports.items()}
    blockers: list[str] = []

    if reports["fire_drill"].get("no_executable_real_order_path_exists") is not True:
        blockers.append("EXECUTABLE_REAL_ORDER_PATH_NOT_EXCLUDED")
    if gate_statuses["watcher"] not in {"AUTONOMOUS_WATCHER_READY", "AUTONOMOUS_WATCHER_NO_ELIGIBLE_MARKET"}:
        blockers.append("WATCHER_NOT_READY")
    if gate_statuses["decision"] not in {"AUTONOMOUS_DECISION_READY", "AUTONOMOUS_DECISION_NO_TRADE"}:
        blockers.append("DECISION_NOT_READY")
    if gate_statuses["intent"] not in {"NO_TRANSMIT_INTENT_READY", "NO_TRANSMIT_INTENT_NO_TRADE"}:
        blockers.append("NO_TRANSMIT_INTENT_NOT_READY")
    if gate_statuses["mock_lifecycle"] != "MOCK_ORDER_LIFECYCLE_PASSED":
        blockers.append("MOCK_ORDER_LIFECYCLE_NOT_PASSED")
    if gate_statuses["fake_execution"] not in {"FAKE_EXECUTION_PASSED", "FAKE_EXECUTION_NO_TRADE"}:
        blockers.append("FAKE_EXECUTION_NOT_PASSED")
    if gate_statuses["post_trade"] != "POST_TRADE_REPORT_READY":
        blockers.append("POST_TRADE_REPORT_NOT_READY")
    if gate_statuses["risk"] != "FIRE_DRILL_RISK_PASSED":
        blockers.append("RISK_NOT_PASSED")
    if reports["risk"].get("kill_switch_status") != "FIRE_DRILL_KILL_SWITCH_PASSED":
        blockers.append("KILL_SWITCH_NOT_PASSED")
    if gate_statuses["reconciliation"] != "FAKE_RECONCILIATION_PASSED":
        blockers.append("RECONCILIATION_NOT_PASSED")
    if gate_statuses["scenarios"] != "FIRE_DRILL_SCENARIOS_PASSED":
        blockers.append("SCENARIOS_NOT_PASSED")
    scenario_names = {
        str(row.get("name"))
        for row in reports["scenarios"].get("scenarios", [])
        if row.get("status") == "PASSED"
    }
    for required in {
        "timeout_self_disable",
        "exception_path_self_disable",
        "reconciliation_mismatch_kill_switch",
        "attempted_auth_endpoint_call",
        "live_flag_true",
    }:
        if required not in scenario_names:
            blockers.append(f"SELF_DISABLE_SCENARIO_MISSING:{required}")

    blockers.extend(_safety_blockers(reports))
    blockers = list(dict.fromkeys(blockers))
    fake_execution = reports["fake_execution"]
    mock_lifecycle = reports["mock_lifecycle"]
    status = SUCCESS if not blockers else "AUTONOMOUS_NO_TRANSMIT_EXECUTION_REHEARSAL_BLOCKED"
    return safety_payload(
        schema_version="autonomous_no_transmit_execution_rehearsal_v1",
        status=status,
        allowed_statuses=[
            SUCCESS,
            "AUTONOMOUS_NO_TRANSMIT_EXECUTION_REHEARSAL_BLOCKED",
        ],
        blockers=blockers,
        gate_statuses=gate_statuses,
        fire_drill_status=gate_statuses["fire_drill"],
        watcher_status=gate_statuses["watcher"],
        decision_status=gate_statuses["decision"],
        post_trade_status=gate_statuses["post_trade"],
        no_transmit_intent_status=gate_statuses["intent"],
        fake_execution_status=gate_statuses["fake_execution"],
        fake_order_state=fake_execution.get("fake_order_state"),
        fake_position_state=fake_execution.get("fake_position_state"),
        fake_pnl=fake_execution.get("fake_pnl", {}),
        mock_accepted_count=mock_lifecycle.get("mock_accepted_count", 0),
        mock_rejected_count=mock_lifecycle.get("mock_rejected_count", 0),
        fake_fills_count=mock_lifecycle.get("fake_fills_count", 0),
        fake_no_fills_count=mock_lifecycle.get("fake_no_fills_count", 0),
        fake_cancels_timeouts_count=mock_lifecycle.get("fake_cancels_timeouts_count", 0),
        no_executable_real_order_path_exists=bool(
            reports["fire_drill"].get("no_executable_real_order_path_exists")
        ),
        request_signing_enabled=False,
        api_keys_loaded=False,
        private_keys_loaded=False,
        authenticated_endpoint_called=False,
        checked_account_balance=False,
        checked_portfolio=False,
        unsafe_action_attempts=0,
        auth_key_order_attempts=0,
        hidden_local_state_dependency=False,
        exact_resume_command=".\\make.cmd sequence59-smoke",
        next_action="Aggregate money-worthy canary-grade readiness."
        if status == SUCCESS
        else "Rerun autonomous live fire-drill smoke and inspect blockers.",
    )


def write_autonomous_no_transmit_execution_rehearsal_report(
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    payload = build_autonomous_no_transmit_execution_rehearsal(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_no_transmit_execution_rehearsal.json",
        md_name="latest_no_transmit_execution_rehearsal.md",
        title="Autonomous No-Transmit Execution Rehearsal",
        summary="Aggregate fake-money rehearsal gate. It does not authorize, sign, route, transmit, or place orders.",
    )
    return payload


def _safety_blockers(reports: dict[str, dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    expected_false = [
        "live_trading_enabled",
        "order_transmission_enabled",
        "authenticated_requests_enabled",
        "request_signing_enabled",
        "api_keys_loaded",
        "private_keys_loaded",
        "authenticated_endpoint_called",
        "checked_account_balance",
        "checked_portfolio",
    ]
    expected_zero = [
        "actual_order_count",
        "actual_cancel_count",
        "unsafe_action_attempts",
        "auth_key_order_attempts",
    ]
    for name, payload in reports.items():
        for key in expected_false:
            if payload.get(key) is True:
                blockers.append(f"UNSAFE_FLAG_TRUE:{name}:{key}")
        for key in expected_zero:
            if int(payload.get(key) or 0) != 0:
                blockers.append(f"UNSAFE_COUNTER_NONZERO:{name}:{key}")
        if payload.get("execution_authority") not in {None, "NONE"}:
            blockers.append(f"EXECUTION_AUTHORITY_NOT_NONE:{name}")
    return blockers
