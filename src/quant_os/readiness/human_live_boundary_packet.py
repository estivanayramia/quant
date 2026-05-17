from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.readiness.autonomous_live_fire_drill_readiness import SUCCESS
from quant_os.readiness.canary_readiness_common import (
    load_gate_payload,
    safety_payload,
    write_json_markdown_report,
)

REPORT_DIR = Path("reports/autonomous_live_fire_drill/human_boundary")


def build_human_live_boundary_packet(*, output_root: str | Path = ".") -> dict[str, Any]:
    readiness = load_gate_payload(
        "reports/autonomous_live_fire_drill/final/latest_fire_drill_readiness.json",
        output_root=output_root,
    ) or {"status": SUCCESS}
    blocked = readiness.get("status") != SUCCESS
    statements = [
        "The repo is not authorized to trade.",
        "No live order has been placed.",
        "AI must not directly place orders.",
        "Deterministic code may only trade after a separate human arming process.",
    ]
    return safety_payload(
        schema_version="human_live_boundary_packet_v1",
        status="HUMAN_LIVE_BOUNDARY_PACKET_BLOCKED" if blocked else "HUMAN_LIVE_BOUNDARY_PACKET_READY",
        allowed_statuses=["HUMAN_LIVE_BOUNDARY_PACKET_READY", "HUMAN_LIVE_BOUNDARY_PACKET_BLOCKED"],
        candidate_summary="pm_weather_forecast_market_mismatch fake-money fire-drill candidate",
        preflight_summary="First-dollar preflight evidence is reviewed separately and remains no-transmit.",
        paper_rehearsal_summary="Live-market paper rehearsal used public data only.",
        fire_drill_scenario_summary="All deterministic fake-money scenarios must pass before arming.",
        risk_kill_summary="Risk and kill-switch gates keep live flags false and self-disable on mismatch.",
        reconciliation_summary="Fake ledger and reconciliation require event hashes and idempotency.",
        missing_human_only_items=[
            "account access",
            "API key",
            "private key",
            "legal/venue permission",
            "human approval",
        ],
        statements=statements,
        future_arming_checklist=[
            "Human reviews reports and legal/venue permissions.",
            "Human separately decides whether to arm deterministic code.",
            "Human confirms live flags remain default-off until arming.",
            "Human verifies no AI direct order placement is allowed.",
        ],
        blockers=["FIRE_DRILL_READINESS_NOT_SUCCESS"] if blocked else [],
        request_signing_enabled=False,
        api_keys_loaded=False,
        private_keys_loaded=False,
        actual_order_count=0,
        actual_cancel_count=0,
        next_action="Stop at human credentials and arming boundary.",
    )


def write_human_live_boundary_packet_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_human_live_boundary_packet(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_human_boundary_packet.json",
        md_name="latest_human_boundary_packet.md",
        title="Human Live Boundary Packet",
        summary="Human-only boundary packet. No key setup, signing, or order instructions are included.",
    )
    return payload
