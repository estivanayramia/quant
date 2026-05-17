from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.readiness.canary_readiness_common import (
    load_gate_payload,
    safety_payload,
    write_json_markdown_report,
)
from quant_os.readiness.first_dollar_provenance_audit import REQUIRED_ARTIFACTS

REPORT_DIR = Path("reports/first_dollar_preflight/final")


def evaluate_first_dollar_preflight(
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    root = Path(output_root)
    missing = [path for path in REQUIRED_ARTIFACTS if not (root / path).exists()]
    reports = {
        "provenance_audit": load_gate_payload(
            "reports/first_dollar_preflight/provenance/latest_provenance_audit.json",
            output_root=output_root,
        )
        or {},
        "provenance_repair": load_gate_payload(
            "reports/first_dollar_preflight/provenance_repair/latest_provenance_repair.json",
            output_root=output_root,
        )
        or {},
        "security": load_gate_payload(
            "reports/first_dollar_preflight/security/latest_first_dollar_security_scan.json",
            output_root=output_root,
        )
        or {},
        "current_market": load_gate_payload(
            "reports/first_dollar_preflight/current_market/latest_current_market_eligibility.json",
            output_root=output_root,
        )
        or {},
        "current_forecast": load_gate_payload(
            "reports/first_dollar_preflight/current_forecast/latest_current_forecast.json",
            output_root=output_root,
        )
        or {},
        "order_preview": load_gate_payload(
            "reports/first_dollar_preflight/order_preview/latest_order_preview.json",
            output_root=output_root,
        )
        or {},
        "human_review": load_gate_payload(
            "reports/first_dollar_preflight/human_review/latest_human_review.json",
            output_root=output_root,
        )
        or {},
        "tiny_canary": load_gate_payload(
            "reports/canary_readiness/final/latest_tiny_canary_readiness.json",
            output_root=output_root,
        )
        or {},
        "manual_packet": load_gate_payload(
            "reports/canary_readiness/manual_packet/latest_manual_canary_packet.json",
            output_root=output_root,
        )
        or {},
    }
    blockers = []
    status = "FIRST_DOLLAR_PREFLIGHT_READY"
    if missing:
        status = "FIRST_DOLLAR_PREFLIGHT_BLOCKED_BY_REPRODUCIBILITY"
        blockers.extend(missing)
    elif reports["provenance_audit"].get("status") != "PROVENANCE_AUDIT_PASSED":
        status = "FIRST_DOLLAR_PREFLIGHT_BLOCKED_BY_PROVENANCE"
        blockers.append("PROVENANCE_AUDIT_PASSED_MISSING")
    elif reports["provenance_repair"].get("status") != "PROVENANCE_REPAIR_PASSED":
        status = "FIRST_DOLLAR_PREFLIGHT_BLOCKED_BY_PROVENANCE"
        blockers.append("PROVENANCE_REPAIR_PASSED_MISSING")
    elif reports["security"].get("status") != "FIRST_DOLLAR_SECURITY_SCAN_PASSED":
        status = "FIRST_DOLLAR_PREFLIGHT_BLOCKED_BY_SECURITY"
        blockers.append("FIRST_DOLLAR_SECURITY_SCAN_PASSED_MISSING")
    elif reports["tiny_canary"].get("status") != "TINY_CANARY_READY_FOR_MANUAL_ARMING":
        status = "FIRST_DOLLAR_PREFLIGHT_BLOCKED_BY_REPRODUCIBILITY"
        blockers.append("TINY_CANARY_READY_FOR_MANUAL_ARMING_MISSING")
    elif reports["manual_packet"].get("status") != "MANUAL_CANARY_PACKET_READY":
        status = "FIRST_DOLLAR_PREFLIGHT_BLOCKED_BY_HUMAN_REVIEW"
        blockers.append("MANUAL_CANARY_PACKET_READY_MISSING")
    elif reports["current_market"].get("status") == "CURRENT_MARKET_ELIGIBILITY_NO_CURRENT_MARKET":
        status = "FIRST_DOLLAR_PREFLIGHT_STRUCTURALLY_READY_NO_CURRENT_MARKET"
        blockers.append("NO_CURRENT_ELIGIBLE_MARKET")
    elif reports["current_market"].get("status") != "CURRENT_MARKET_ELIGIBILITY_PASSED":
        status = "FIRST_DOLLAR_PREFLIGHT_BLOCKED_BY_CURRENT_MARKET"
        blockers.append("CURRENT_MARKET_ELIGIBILITY_PASSED_MISSING")
    elif reports["current_forecast"].get("status") != "CURRENT_FORECAST_MATCHED":
        status = "FIRST_DOLLAR_PREFLIGHT_BLOCKED_BY_FORECAST"
        blockers.append("CURRENT_FORECAST_MATCHED_MISSING")
    elif reports["order_preview"].get("status") != "NO_TRANSMIT_ORDER_PREVIEW_READY":
        status = "FIRST_DOLLAR_PREFLIGHT_BLOCKED_BY_ORDER_PREVIEW"
        blockers.append("NO_TRANSMIT_ORDER_PREVIEW_READY_MISSING")
    elif reports["human_review"].get("status") != "HUMAN_REVIEW_PACKET_READY":
        status = "FIRST_DOLLAR_PREFLIGHT_BLOCKED_BY_HUMAN_REVIEW"
        blockers.append("HUMAN_REVIEW_PACKET_READY_MISSING")
    payload = safety_payload(
        schema_version="first_dollar_preflight_v1",
        status=status,
        allowed_statuses=[
            "FIRST_DOLLAR_PREFLIGHT_READY",
            "FIRST_DOLLAR_PREFLIGHT_BLOCKED_BY_REPRODUCIBILITY",
            "FIRST_DOLLAR_PREFLIGHT_BLOCKED_BY_PROVENANCE",
            "FIRST_DOLLAR_PREFLIGHT_BLOCKED_BY_SECURITY",
            "FIRST_DOLLAR_PREFLIGHT_BLOCKED_BY_CURRENT_MARKET",
            "FIRST_DOLLAR_PREFLIGHT_BLOCKED_BY_FORECAST",
            "FIRST_DOLLAR_PREFLIGHT_BLOCKED_BY_ORDER_PREVIEW",
            "FIRST_DOLLAR_PREFLIGHT_BLOCKED_BY_HUMAN_REVIEW",
            "FIRST_DOLLAR_PREFLIGHT_STRUCTURALLY_READY_NO_CURRENT_MARKET",
        ],
        candidate_id="pm_weather_forecast_market_mismatch",
        missing_artifacts=missing,
        component_statuses={key: value.get("status") for key, value in reports.items()},
        tiny_canary_readiness_status=reports["tiny_canary"].get("status"),
        manual_canary_packet_status=reports["manual_packet"].get("status"),
        human_action_required_before_first_dollar=True,
        separate_manual_action_required_for_first_dollar=True,
        api_keys_loaded=False,
        private_keys_loaded=False,
        authenticated_requests_enabled=False,
        order_transmission_enabled=False,
        actual_order_count=0,
        actual_cancel_count=0,
        blockers=blockers,
        next_action="Wait for an eligible current public market, then repeat public-only eligibility checks."
        if status == "FIRST_DOLLAR_PREFLIGHT_STRUCTURALLY_READY_NO_CURRENT_MARKET"
        else "Human review remains required before any first-dollar action."
        if status == "FIRST_DOLLAR_PREFLIGHT_READY"
        else "Resolve the blocking first-dollar preflight component.",
    )
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_first_dollar_preflight.json",
        md_name="latest_first_dollar_preflight.md",
        title="Final First-Dollar Preflight",
        summary="Final no-transmit first-dollar preflight. This report does not arm or send orders.",
    )
    return payload


def write_first_dollar_preflight_report(
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    return evaluate_first_dollar_preflight(output_root=output_root)
