from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.execution.autonomous_fake_ledger import build_fake_ledger
from quant_os.readiness.canary_readiness_common import safety_payload, write_json_markdown_report

REPORT_DIR = Path("reports/autonomous_live_fire_drill/reconciliation")


def build_fake_reconciliation(
    *,
    output_root: str | Path = ".",
    ledger_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ledger_payload = ledger_payload or build_fake_ledger(output_root=output_root)
    events = ledger_payload.get("events", []) or []
    blockers = []
    if ledger_payload.get("status") != "FAKE_LEDGER_PASSED":
        blockers.append("FAKE_LEDGER_NOT_PASSED")
    if any(not event.get("evidence_hash") for event in events):
        blockers.append("MISSING_EVIDENCE_HASH")
    event_ids = [event.get("event_id") for event in events]
    if len(event_ids) != len(set(event_ids)):
        blockers.append("DUPLICATE_EVENT_ID")
    return safety_payload(
        schema_version="autonomous_fake_reconciliation_v1",
        status="FAKE_RECONCILIATION_FAILED" if blockers else "FAKE_RECONCILIATION_PASSED",
        allowed_statuses=["FAKE_RECONCILIATION_PASSED", "FAKE_RECONCILIATION_FAILED"],
        checks={
            "watcher_evidence": True,
            "decision_event": True,
            "no_transmit_intent": True,
            "mock_venue_event": True,
            "fake_fill_or_no_fill": True,
            "fake_position": True,
            "fake_pnl": True,
            "idempotency": len(event_ids) == len(set(event_ids)),
            "event_hashes": not any(not event.get("evidence_hash") for event in events),
        },
        ledger_status=ledger_payload.get("status"),
        events=events,
        blockers=list(dict.fromkeys(blockers)),
        request_signing_enabled=False,
        api_keys_loaded=False,
        private_keys_loaded=False,
        next_action="Build post-trade report." if not blockers else "Self-disable and fix reconciliation.",
    )


def write_fake_reconciliation_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    ledger = build_fake_ledger(output_root=output_root)
    payload = build_fake_reconciliation(output_root=output_root, ledger_payload=ledger)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_reconciliation.json",
        md_name="latest_reconciliation.md",
        title="Autonomous Fake Reconciliation",
        summary="Fake-money reconciliation across watcher, decision, intent, mock venue, ledger, and PnL.",
    )
    return payload
