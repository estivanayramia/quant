from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.readiness.canary_readiness_common import (
    load_gate_payload,
    safety_payload,
    update_canary_state,
    write_json_markdown_report,
)
from quant_os.readiness.weather_manual_canary_packet import GATE_REPORTS

REPORT_DIR = Path("reports/canary_readiness/final")

EXPECTED = {
    "paper_candidate_audit": ("PAPER_CANDIDATE_AUDIT_PASSED", "TINY_CANARY_BLOCKED_BY_AUDIT"),
    "lineage_audit": ("LINEAGE_AUDIT_PASSED", "TINY_CANARY_BLOCKED_BY_LINEAGE"),
    "replay_recompute": ("REPLAY_RECOMPUTE_MATCHED", "TINY_CANARY_BLOCKED_BY_REPLAY"),
    "robustness": ("ROBUSTNESS_PASSED", "TINY_CANARY_BLOCKED_BY_ROBUSTNESS"),
    "cost_fill_stress": ("COST_FILL_STRESS_PASSED", "TINY_CANARY_BLOCKED_BY_COST_FILL"),
    "shadow_rehearsal": ("BOUNDED_SHADOW_REHEARSAL_PASSED", "TINY_CANARY_BLOCKED_BY_SHADOW"),
    "dry_run_parity": ("DRY_RUN_PARITY_PASSED", "TINY_CANARY_BLOCKED_BY_DRY_RUN"),
    "risk": ("TINY_CANARY_RISK_PASSED", "TINY_CANARY_BLOCKED_BY_RISK"),
    "kill_switch": ("KILL_SWITCH_PROOF_PASSED", "TINY_CANARY_BLOCKED_BY_KILL_SWITCH"),
    "reconciliation": ("RECONCILIATION_PROOF_PASSED", "TINY_CANARY_BLOCKED_BY_RECONCILIATION"),
    "manual_packet": ("MANUAL_CANARY_PACKET_READY", "TINY_CANARY_BLOCKED_BY_MANUAL_PACKET"),
}


def evaluate_tiny_canary_readiness(
    *,
    gate_payloads: dict[str, dict[str, Any]] | None = None,
    api_keys_loaded: bool = False,
    private_keys_loaded: bool = False,
    authenticated_requests_enabled: bool = False,
    actual_order_count: int = 0,
    actual_cancel_count: int = 0,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    if gate_payloads is None:
        gate_payloads = {
            key: load_gate_payload(path, output_root=output_root) or {}
            for key, path in {
                **GATE_REPORTS,
                "manual_packet": "reports/canary_readiness/manual_packet/latest_manual_canary_packet.json",
            }.items()
        }
    status = "TINY_CANARY_READY_FOR_MANUAL_ARMING"
    blockers: list[str] = []
    for gate, (expected, blocked_status) in EXPECTED.items():
        if gate_payloads.get(gate, {}).get("status") != expected:
            status = blocked_status
            blockers.append(f"{gate}:{expected}_MISSING")
            break
    unsafe_requested = api_keys_loaded or private_keys_loaded or authenticated_requests_enabled
    if unsafe_requested:
        status = "NEEDS_HUMAN_APPROVAL_FOR_FIRST_DOLLAR_TRADE"
        blockers.append("CREDENTIAL_OR_AUTHORITY_REQUEST_BLOCKED")
    if actual_order_count or actual_cancel_count:
        status = "NEEDS_HUMAN_APPROVAL_FOR_FIRST_DOLLAR_TRADE"
        blockers.append("NONZERO_ORDER_OR_CANCEL_COUNT_BLOCKED")
    payload = safety_payload(
        schema_version="tiny_canary_readiness_v1",
        status=status,
        allowed_statuses=[
            "TINY_CANARY_READY_FOR_MANUAL_ARMING",
            "TINY_CANARY_BLOCKED_BY_AUDIT",
            "TINY_CANARY_BLOCKED_BY_LINEAGE",
            "TINY_CANARY_BLOCKED_BY_REPLAY",
            "TINY_CANARY_BLOCKED_BY_ROBUSTNESS",
            "TINY_CANARY_BLOCKED_BY_COST_FILL",
            "TINY_CANARY_BLOCKED_BY_SHADOW",
            "TINY_CANARY_BLOCKED_BY_DRY_RUN",
            "TINY_CANARY_BLOCKED_BY_RISK",
            "TINY_CANARY_BLOCKED_BY_KILL_SWITCH",
            "TINY_CANARY_BLOCKED_BY_RECONCILIATION",
            "TINY_CANARY_BLOCKED_BY_MANUAL_PACKET",
            "NEEDS_HUMAN_APPROVAL_FOR_FIRST_DOLLAR_TRADE",
        ],
        candidate_id="pm_weather_forecast_market_mismatch",
        gate_statuses={key: value.get("status") for key, value in gate_payloads.items()},
        api_keys_loaded=False,
        private_keys_loaded=False,
        authenticated_requests_enabled=False,
        actual_order_count=0,
        actual_cancel_count=0,
        order_transmission_enabled=False,
        manual_approval_required=True,
        first_dollar_preflight_command="python -m quant_os.cli readiness tiny-canary-readiness",
        post_canary_reconciliation_command="python -m quant_os.cli execution weather-canary-reconciliation",
        blockers=blockers,
        next_action="Human may manually review the packet; repository must still not transmit orders."
        if status == "TINY_CANARY_READY_FOR_MANUAL_ARMING"
        else "Resolve the blocking canary gate.",
    )
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_tiny_canary_readiness.json",
        md_name="latest_tiny_canary_readiness.md",
        title="Final Tiny Canary Readiness",
        summary="Final no-transmit readiness report before any human manual arming decision.",
    )
    update_canary_state(
        output_root=output_root,
        gate="final",
        gate_status=status,
        evidence_paths=payload["report_paths"],
        gates_passed=["final"] if status == "TINY_CANARY_READY_FOR_MANUAL_ARMING" else [],
        gates_failed=[] if status == "TINY_CANARY_READY_FOR_MANUAL_ARMING" else ["final"],
        blocker=blockers[0] if blockers else None,
        next_action=payload["next_action"],
        validation_status="PENDING_FULL_VALIDATION",
    )
    return payload


def write_tiny_canary_readiness_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    return evaluate_tiny_canary_readiness(output_root=output_root)
