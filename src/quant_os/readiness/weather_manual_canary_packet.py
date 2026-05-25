from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.readiness.canary_readiness_common import (
    load_gate_payload,
    safety_payload,
    update_canary_state,
    write_json_markdown_report,
)

REPORT_DIR = Path("reports/canary_readiness/manual_packet")

GATE_REPORTS = {
    "paper_candidate_audit": "reports/canary_readiness/paper_candidate_audit/latest_paper_candidate_audit.json",
    "lineage_audit": "reports/canary_readiness/lineage_audit/latest_lineage_audit.json",
    "replay_recompute": "reports/canary_readiness/replay_recompute/latest_replay_recompute.json",
    "robustness": "reports/canary_readiness/robustness/latest_robustness.json",
    "cost_fill_stress": "reports/canary_readiness/cost_fill_stress/latest_cost_fill_stress.json",
    "shadow_rehearsal": "reports/canary_readiness/shadow_rehearsal/latest_shadow_rehearsal.json",
    "dry_run_parity": "reports/canary_readiness/dry_run_parity/latest_dry_run_parity.json",
    "risk": "reports/canary_readiness/risk/latest_tiny_canary_risk.json",
    "kill_switch": "reports/canary_readiness/kill_switch/latest_kill_switch.json",
    "reconciliation": "reports/canary_readiness/reconciliation/latest_reconciliation.json",
}

EXPECTED = {
    "paper_candidate_audit": "PAPER_CANDIDATE_AUDIT_PASSED",
    "lineage_audit": "LINEAGE_AUDIT_PASSED",
    "replay_recompute": "REPLAY_RECOMPUTE_MATCHED",
    "robustness": "ROBUSTNESS_PASSED",
    "cost_fill_stress": "COST_FILL_STRESS_PASSED",
    "shadow_rehearsal": "BOUNDED_SHADOW_REHEARSAL_PASSED",
    "dry_run_parity": "DRY_RUN_PARITY_PASSED",
    "risk": "TINY_CANARY_RISK_PASSED",
    "kill_switch": "KILL_SWITCH_PROOF_PASSED",
    "reconciliation": "RECONCILIATION_PROOF_PASSED",
}


def build_manual_canary_packet(
    *,
    gate_payloads: dict[str, dict[str, Any]] | None = None,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    if gate_payloads is None:
        gate_payloads = {
            key: load_gate_payload(path, output_root=output_root) or {}
            for key, path in GATE_REPORTS.items()
        }
    blockers = [
        f"{key}:{EXPECTED[key]}_MISSING"
        for key, expected in EXPECTED.items()
        if gate_payloads.get(key, {}).get("status") != expected
    ]
    status = "MANUAL_CANARY_PACKET_READY" if not blockers else "MANUAL_CANARY_PACKET_BLOCKED"
    payload = safety_payload(
        schema_version="weather_manual_canary_packet_v1",
        status=status,
        allowed_statuses=["MANUAL_CANARY_PACKET_READY", "MANUAL_CANARY_PACKET_BLOCKED"],
        candidate_summary={
            "candidate_id": "pm_weather_forecast_market_mismatch",
            "family": "weather / Kalshi weather-market mismatch using historical IEM MOS forecasts",
            "statement": "This packet does not place or authorize an order.",
        },
        evidence_paths=GATE_REPORTS,
        audit_results={key: value.get("status") for key, value in gate_payloads.items()},
        shadow_rehearsal_result=gate_payloads.get("shadow_rehearsal", {}).get("status"),
        dry_run_parity_result=gate_payloads.get("dry_run_parity", {}).get("status"),
        risk_envelope=gate_payloads.get("risk", {}).get("risk_envelope", {}),
        kill_switch_proof=gate_payloads.get("kill_switch", {}).get("status"),
        reconciliation_proof=gate_payloads.get("reconciliation", {}).get("status"),
        market_eligibility_checklist=[
            "Market is the audited weather candidate market.",
            "Forecast and market timestamps satisfy lineage invariant.",
            "Current spread and liquidity pass the kill-switch matrix.",
            "Manual review confirms the tiny canary envelope.",
        ],
        no_trade_checklist=[
            "No trade if any gate report is missing or failed.",
            "No trade if data is stale, forecast missing, market data missing, spread wide, or liquidity thin.",
            "No trade if reconciliation from any prior canary is missing.",
            "No trade if manual stop is active.",
        ],
        manual_approval_checkbox=False,
        required_human_confirmations=[
            "I reviewed all report paths.",
            "I accept the tiny one-order envelope.",
            "I understand this repository did not transmit an order.",
        ],
        first_dollar_preflight_command="python -m quant_os.cli readiness tiny-canary-readiness",
        post_canary_reconciliation_command="python -m quant_os.cli execution weather-canary-reconciliation",
        rollback_abort_instructions=[
            "Leave live trading disabled.",
            "Do not arm if any report status changes.",
            "Use the kill switch and stop before transmission if any preflight changes.",
        ],
        blockers=blockers,
        next_action="Run final tiny canary readiness." if status == "MANUAL_CANARY_PACKET_READY" else "Resolve missing gate report before packet use.",
    )
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_manual_canary_packet.json",
        md_name="latest_manual_canary_packet.md",
        title="Weather Manual Canary Packet",
        summary="Human review packet for a future manual tiny canary decision.",
    )
    update_canary_state(
        output_root=output_root,
        gate="manual_packet",
        gate_status=status,
        evidence_paths=payload["report_paths"],
        gates_passed=["manual_packet"] if status == "MANUAL_CANARY_PACKET_READY" else [],
        gates_failed=[] if status == "MANUAL_CANARY_PACKET_READY" else ["manual_packet"],
        blocker=blockers[0] if blockers else None,
        next_action=payload["next_action"],
    )
    return payload


def write_weather_manual_canary_packet_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    return build_manual_canary_packet(output_root=output_root)
