from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.autonomy.canary_grade_live_sim_common import RESUME_COMMAND, canary_safe_payload
from quant_os.autonomy.live_market_sim_common import load_json
from quant_os.readiness.canary_readiness_common import write_json_markdown_report

REPORT_DIR = Path("reports/canary_grade_live_sim/money_worthy")
SUCCESS = "MONEY_WORTHY_CANARY_GRADE_PROFITABILITY_PROVEN"


def build_money_worthy_canary_grade(
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    readiness = load_json(
        "reports/canary_grade_live_sim/final/latest_canary_grade_live_sim_readiness.json",
        output_root=output_root,
    ) or {}
    packet = load_json(
        "reports/canary_grade_live_sim/manual_canary_packet/latest_manual_canary_packet.json",
        output_root=output_root,
    ) or {}
    rehearsal = load_json(
        (
            "reports/autonomous_live_fire_drill/no_transmit_execution_rehearsal/"
            "latest_no_transmit_execution_rehearsal.json"
        ),
        output_root=output_root,
    ) or {}
    blockers: list[str] = []

    if readiness.get("status") != "CANARY_GRADE_LIVE_SIM_PROFITABILITY_PROVEN":
        blockers.append("CANARY_GRADE_LIVE_SIM_PROFITABILITY_NOT_PROVEN")
    if packet.get("status") != "FIRST_TINY_MANUAL_CANARY_PACKET_READY":
        blockers.append("FIRST_TINY_MANUAL_CANARY_PACKET_NOT_READY")
    if rehearsal.get("status") != "AUTONOMOUS_NO_TRANSMIT_EXECUTION_REHEARSAL_PASSED":
        blockers.append("AUTONOMOUS_NO_TRANSMIT_EXECUTION_REHEARSAL_NOT_PASSED")
    if float(readiness.get("fake_net_pnl") or 0.0) <= 0.0:
        blockers.append("FAKE_NET_PNL_NOT_POSITIVE")
    if readiness.get("baseline_beaten") is not True:
        blockers.append("BASELINE_NOT_BEATEN")
    if readiness.get("placebo_beaten") is not True:
        blockers.append("PLACEBO_NOT_BEATEN")
    if int(readiness.get("reconciliation_failures") or 0) != 0:
        blockers.append("RECONCILIATION_FAILURES_PRESENT")
    blockers.extend(_safety_blockers({"readiness": readiness, "packet": packet, "rehearsal": rehearsal}))

    blockers = list(dict.fromkeys(blockers))
    status = SUCCESS if not blockers else _blocked_status(blockers)
    return canary_safe_payload(
        schema_version="money_worthy_canary_grade_v1",
        status=status,
        allowed_statuses=[
            SUCCESS,
            "MONEY_WORTHY_CANARY_GRADE_NOT_PROVEN",
            "MONEY_WORTHY_CANARY_GRADE_BLOCKED_BY_PACKET",
            "MONEY_WORTHY_CANARY_GRADE_BLOCKED_BY_REHEARSAL",
            "MONEY_WORTHY_CANARY_GRADE_BLOCKED_BY_SAFETY",
        ],
        blockers=blockers,
        active_market_family=readiness.get("active_market_family"),
        active_strategy=readiness.get("active_strategy"),
        assets_tested=readiness.get("assets_tested", []),
        venues_tested=readiness.get("venues_tested", []),
        observations_count=int(readiness.get("observations_count") or 0),
        eligible_intent_count=int(readiness.get("eligible_intent_count") or 0),
        fake_fill_count=int(readiness.get("fake_fill_count") or 0),
        completed_mark_count=int(readiness.get("completed_mark_count") or 0),
        fake_gross_pnl=float(readiness.get("fake_gross_pnl") or 0.0),
        fake_net_pnl=float(readiness.get("fake_net_pnl") or 0.0),
        baseline_pnl=float(readiness.get("baseline_pnl") or 0.0),
        placebo_pnl=float(readiness.get("placebo_pnl") or 0.0),
        baseline_beaten=readiness.get("baseline_beaten") is True,
        placebo_beaten=readiness.get("placebo_beaten") is True,
        repeatability_status=readiness.get("repeatability_status"),
        capacity_status=readiness.get("capacity_status"),
        fresh_repro_status=readiness.get("fresh_repro_status"),
        manual_packet_status=packet.get("status"),
        no_transmit_execution_rehearsal_status=rehearsal.get("status"),
        reconciliation_failures=int(readiness.get("reconciliation_failures") or 0),
        canary_grade_readiness_status=readiness.get("status"),
        exact_resume_command=".\\make.cmd money-worthy-canary-grade-public-run"
        if status == SUCCESS
        else RESUME_COMMAND,
        next_action="Profitability proof is ready for human review; no order is authorized."
        if status == SUCCESS
        else "Continue canary-grade public proof, packet, and no-transmit rehearsal gates.",
    )


def write_money_worthy_canary_grade_report(
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    payload = build_money_worthy_canary_grade(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_money_worthy_canary_grade.json",
        md_name="latest_money_worthy_canary_grade.md",
        title="Money-Worthy Canary-Grade Readiness",
        summary="Aggregate fake-money profitability gate for canary-grade public-market simulation.",
    )
    return payload


def _blocked_status(blockers: list[str]) -> str:
    if any(blocker.startswith("UNSAFE_") or blocker.startswith("EXECUTION_") for blocker in blockers):
        return "MONEY_WORTHY_CANARY_GRADE_BLOCKED_BY_SAFETY"
    if "FIRST_TINY_MANUAL_CANARY_PACKET_NOT_READY" in blockers:
        return "MONEY_WORTHY_CANARY_GRADE_BLOCKED_BY_PACKET"
    if "AUTONOMOUS_NO_TRANSMIT_EXECUTION_REHEARSAL_NOT_PASSED" in blockers:
        return "MONEY_WORTHY_CANARY_GRADE_BLOCKED_BY_REHEARSAL"
    return "MONEY_WORTHY_CANARY_GRADE_NOT_PROVEN"


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
    ]
    expected_zero = ["actual_order_count", "actual_cancel_count", "unsafe_action_attempts"]
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
