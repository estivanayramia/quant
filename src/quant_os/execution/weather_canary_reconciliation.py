from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.execution.weather_canary_ledger import build_canary_ledger_events
from quant_os.readiness.canary_readiness_common import (
    safety_payload,
    update_canary_state,
    write_json_markdown_report,
)

REPORT_DIR = Path("reports/canary_readiness/reconciliation")


def evaluate_reconciliation_proof(
    *,
    evidence_hash: str = "sha256:manual-canary-evidence",
    duplicate_idempotency_key: bool = False,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    events = build_canary_ledger_events(
        evidence_hash=evidence_hash,
        duplicate_idempotency_key=duplicate_idempotency_key,
    )
    keys = [event["idempotency_key"] for event in events]
    blockers: list[str] = []
    if len(keys) != len(set(keys)):
        blockers.append("DUPLICATE_IDEMPOTENCY_KEY")
    if any(not event.get("evidence_hash") for event in events):
        blockers.append("MISSING_EVIDENCE_HASH")
    if any(event.get("offline_only") is not True or event.get("no_send") is not True for event in events):
        blockers.append("UNSAFE_LEDGER_EVENT")
    status = "RECONCILIATION_PROOF_PASSED" if not blockers else "RECONCILIATION_PROOF_FAILED"
    payload = safety_payload(
        schema_version="weather_canary_reconciliation_v1",
        status=status,
        allowed_statuses=[
            "RECONCILIATION_PROOF_PASSED",
            "RECONCILIATION_PROOF_FAILED",
            "LEDGER_SCHEMA_INCOMPLETE",
        ],
        candidate_id="pm_weather_forecast_market_mismatch",
        ledger_events=events,
        post_canary_report_schema={
            "evidence_hash": "required",
            "order_intent_event": "required",
            "manual_approval_event": "required",
            "fill_or_no_fill_event": "placeholder_until_human_action",
            "settlement_reconciliation_event": "placeholder_until_resolution",
            "unknown_position_state": "blocked",
        },
        blockers=blockers,
        next_action="Build manual canary arming packet." if status == "RECONCILIATION_PROOF_PASSED" else "Fix ledger idempotency or schema.",
    )
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_reconciliation.json",
        md_name="latest_reconciliation.md",
        title="Weather Canary Reconciliation",
        summary="Defines offline ledger and reconciliation placeholders.",
    )
    update_canary_state(
        output_root=output_root,
        gate="reconciliation",
        gate_status=status,
        evidence_paths=payload["report_paths"],
        gates_passed=["reconciliation"] if status == "RECONCILIATION_PROOF_PASSED" else [],
        gates_failed=[] if status == "RECONCILIATION_PROOF_PASSED" else ["reconciliation"],
        blocker=blockers[0] if blockers else None,
        next_action=payload["next_action"],
    )
    return payload


def write_weather_canary_reconciliation_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    return evaluate_reconciliation_proof(output_root=output_root)
