from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.readiness.canary_readiness_common import (
    load_gate_payload,
    safety_payload,
    write_json_markdown_report,
)

REPORT_DIR = Path("reports/autonomous_live_fire_drill/no_transmit_intent")


def build_no_transmit_intent(
    *,
    output_root: str | Path = ".",
    decision_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision_payload = decision_payload or load_gate_payload(
        "reports/autonomous_live_fire_drill/decision/latest_decision.json",
        output_root=output_root,
    ) or {}
    blockers = list(decision_payload.get("blockers", []) or [])
    if decision_payload.get("status") != "AUTONOMOUS_DECISION_READY":
        status = "NO_TRANSMIT_INTENT_NO_TRADE"
        intent = None
    elif not decision_payload.get("forecast_evidence_hash") or not decision_payload.get("market_evidence_hash"):
        status = "NO_TRANSMIT_INTENT_BLOCKED"
        blockers.append("MISSING_EVIDENCE_HASH")
        intent = None
    else:
        status = "NO_TRANSMIT_INTENT_READY"
        intent = {
            "candidate_id": decision_payload.get("candidate_id"),
            "market_ticker": decision_payload.get("market_ticker"),
            "side": decision_payload.get("side"),
            "action": decision_payload.get("action"),
            "limit_price": decision_payload.get("limit_price"),
            "max_contracts": decision_payload.get("max_contracts"),
            "max_nominal_exposure": decision_payload.get("max_nominal_exposure"),
            "max_total_loss": decision_payload.get("max_total_loss"),
            "reason_code": decision_payload.get("reason_code"),
            "forecast_evidence_hash": decision_payload.get("forecast_evidence_hash"),
            "market_evidence_hash": decision_payload.get("market_evidence_hash"),
            "client_order_id_preview": decision_payload.get("client_order_id_preview"),
            "fake_money": True,
            "dry_run_only": True,
            "no_send": True,
            "order_transmission_enabled": False,
            "authenticated_requests_enabled": False,
            "api_keys_loaded": False,
            "private_keys_loaded": False,
            "contains_signed_headers": False,
            "contains_private_key_path": False,
            "contains_executable_submission_code": False,
        }
    return safety_payload(
        schema_version="autonomous_no_transmit_intent_v1",
        status=status,
        allowed_statuses=[
            "NO_TRANSMIT_INTENT_READY",
            "NO_TRANSMIT_INTENT_NO_TRADE",
            "NO_TRANSMIT_INTENT_BLOCKED",
        ],
        intent=intent,
        blockers=list(dict.fromkeys(blockers)),
        fake_money=True,
        dry_run_only=True,
        no_send=True,
        request_signing_enabled=False,
        api_keys_loaded=False,
        private_keys_loaded=False,
        next_action="Run local mock venue lifecycle."
        if status == "NO_TRANSMIT_INTENT_READY"
        else "Record no-trade and continue watcher loop.",
    )


def write_no_transmit_intent_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_no_transmit_intent(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_intent.json",
        md_name="latest_intent.md",
        title="Autonomous No-Transmit Intent",
        summary="Fake-money dry-run-only order intent. It cannot submit, sign, or authenticate.",
    )
    return payload
