from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.autonomy.canary_grade_live_sim_common import canary_safe_payload
from quant_os.autonomy.live_market_sim_common import load_json
from quant_os.readiness.canary_readiness_common import (
    write_json_markdown_report,
)

REPORT_DIR = Path("reports/canary_grade_live_sim/armability")
SUCCESS = "ARMABLE_FOR_HUMAN_GOVERNED_AUTONOMOUS_EXECUTION_REVIEW"


def build_canary_grade_armability(*, output_root: str | Path = ".") -> dict[str, Any]:
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
    fresh_repro = load_json(
        "reports/canary_grade_live_sim/fresh_repro/latest_fresh_repro.json",
        output_root=output_root,
    ) or {}
    money_worthy = load_json(
        "reports/canary_grade_live_sim/money_worthy/latest_money_worthy_canary_grade.json",
        output_root=output_root,
    ) or {}

    blockers: list[str] = []
    if money_worthy.get("status") != "MONEY_WORTHY_CANARY_GRADE_PROFITABILITY_PROVEN":
        blockers.append("MONEY_WORTHY_CANARY_GRADE_PROFITABILITY_NOT_PROVEN")
    if packet.get("status") != "FIRST_TINY_MANUAL_CANARY_PACKET_READY":
        blockers.append("FIRST_TINY_MANUAL_CANARY_PACKET_NOT_READY")
    if rehearsal.get("status") != "AUTONOMOUS_NO_TRANSMIT_EXECUTION_REHEARSAL_PASSED":
        blockers.append("AUTONOMOUS_NO_TRANSMIT_EXECUTION_REHEARSAL_NOT_PASSED")
    if _independent_fresh_worktree_status(fresh_repro) != "INDEPENDENT_FRESH_WORKTREE_PROOF_PASSED":
        blockers.append("INDEPENDENT_FRESH_WORKTREE_PROOF_NOT_PASSED")
    if readiness.get("status") != "CANARY_GRADE_LIVE_SIM_PROFITABILITY_PROVEN":
        blockers.append("CANARY_GRADE_LIVE_SIM_PROFITABILITY_NOT_PROVEN")
    if float(readiness.get("fake_net_pnl") or money_worthy.get("fake_net_pnl") or 0.0) <= 0.0:
        blockers.append("FAKE_NET_PNL_NOT_POSITIVE")
    if readiness.get("baseline_beaten") is not True:
        blockers.append("BASELINE_NOT_BEATEN")
    if readiness.get("placebo_beaten") is not True:
        blockers.append("PLACEBO_NOT_BEATEN")
    blockers.extend(
        _safety_blockers(
            {
                "readiness": readiness,
                "packet": packet,
                "rehearsal": rehearsal,
                "fresh_repro": fresh_repro,
                "money_worthy": money_worthy,
            }
        )
    )

    blockers = list(dict.fromkeys(blockers))
    status = SUCCESS if not blockers else "ARMABILITY_BLOCKED"
    return canary_safe_payload(
        schema_version="canary_grade_armability_v1",
        status=status,
        allowed_statuses=[SUCCESS, "ARMABILITY_BLOCKED"],
        blockers=blockers,
        money_worthy_status=money_worthy.get("status"),
        canary_grade_readiness_status=readiness.get("status"),
        manual_packet_status=packet.get("status"),
        no_transmit_execution_rehearsal_status=rehearsal.get("status"),
        independent_fresh_worktree_proof_status=_independent_fresh_worktree_status(fresh_repro),
        independent_clean_checkout_verified=(
            fresh_repro.get("independent_clean_checkout_verified") is True
        ),
        fake_net_pnl=float(readiness.get("fake_net_pnl") or money_worthy.get("fake_net_pnl") or 0.0),
        baseline_beaten=readiness.get("baseline_beaten") is True,
        placebo_beaten=readiness.get("placebo_beaten") is True,
        review_scope="human_governed_autonomous_no_transmit_execution_review",
        no_real_order_authority=True,
        human_credentials_account_legal_approval_remain_separate=True,
        hidden_local_state_dependency=False,
        exact_resume_command=".\\make.cmd money-worthy-canary-grade-public-run",
        next_action=(
            "Human may review deterministic no-transmit autonomy; real credentials and "
            "live order authority remain separate and disabled."
            if status == SUCCESS
            else "Continue fresh public canary proof and independent clean-worktree validation."
        ),
    )


def write_canary_grade_armability_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_canary_grade_armability(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_armability.json",
        md_name="latest_armability.md",
        title="Canary-Grade Human-Governed Armability",
        summary=(
            "Armability gate for deterministic no-transmit autonomous review. "
            "It does not authorize credentials, signing, routing, transmission, or orders."
        ),
    )
    return payload


def _independent_fresh_worktree_status(fresh_repro: dict[str, Any]) -> str:
    explicit = str(fresh_repro.get("independent_fresh_worktree_proof_status") or "")
    if explicit:
        return explicit
    if (
        fresh_repro.get("independent_clean_checkout_verified") is True
        and fresh_repro.get("status")
        in {"FRESH_REPRO_PASSED", "INDEPENDENT_FRESH_WORKTREE_PROOF_PASSED"}
    ):
        return "INDEPENDENT_FRESH_WORKTREE_PROOF_PASSED"
    return "INDEPENDENT_FRESH_WORKTREE_PROOF_BLOCKED"


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
