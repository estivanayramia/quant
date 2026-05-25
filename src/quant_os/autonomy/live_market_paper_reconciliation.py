from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.readiness.canary_readiness_common import (
    load_gate_payload,
    safety_payload,
    write_json_markdown_report,
)

REPORT_DIR = Path("reports/live_market_paper_rehearsal/reconciliation")
STATE_JSON = Path("reports/live_market_paper_rehearsal/state/latest_state.json")


def build_live_market_paper_reconciliation(*, output_root: str | Path = ".") -> dict[str, Any]:
    intents = load_gate_payload(
        "reports/live_market_paper_rehearsal/intents/latest_intents.json",
        output_root=output_root,
    ) or {}
    fills = load_gate_payload(
        "reports/live_market_paper_rehearsal/fills/latest_fake_fills.json",
        output_root=output_root,
    ) or {}
    ledger = load_gate_payload(
        "reports/live_market_paper_rehearsal/ledger/latest_paper_ledger.json",
        output_root=output_root,
    ) or {}
    intent = intents.get("intent")
    fake_fill = fills.get("fake_fill")
    ledger_events = ledger.get("ledger_events", []) or []
    keys = [event.get("idempotency_key") for event in ledger_events]
    checks = {
        "intent_vs_fake_fill": bool(intent) == bool(fake_fill) or fills.get("status") == "FAKE_NO_FILL",
        "fake_fill_vs_ledger": not fake_fill
        or any(event.get("fake_fill_id") == fake_fill.get("fake_fill_id") for event in ledger_events),
        "ledger_vs_position": bool(ledger.get("fake_position")),
        "no_trade_no_fill_consistent": intent is None and fake_fill is None
        and intents.get("status") == "PAPER_INTENT_NO_TRADE"
        and fills.get("status") == "FAKE_NO_FILL",
        "no_duplicate_events": len(keys) == len(set(keys)),
        "no_missing_evidence_hashes": all(event.get("evidence_hash") for event in ledger_events),
    }
    blockers = []
    if not checks["no_duplicate_events"]:
        blockers.append("DUPLICATE_LEDGER_EVENT")
    if not checks["no_missing_evidence_hashes"]:
        blockers.append("MISSING_EVIDENCE_HASH")
    if intent and (not intent.get("forecast_evidence_hash") or not intent.get("market_evidence_hash")):
        blockers.append("MISSING_INTENT_EVIDENCE_HASH")
    if not checks["intent_vs_fake_fill"]:
        blockers.append("INTENT_FILL_MISMATCH")
    if not checks["fake_fill_vs_ledger"]:
        blockers.append("FILL_LEDGER_MISMATCH")
    status = "PAPER_RECONCILIATION_PASSED" if not blockers else "PAPER_RECONCILIATION_FAILED"
    return safety_payload(
        schema_version="live_market_paper_reconciliation_v1",
        status=status,
        allowed_statuses=[
            "PAPER_RECONCILIATION_PASSED",
            "PAPER_RECONCILIATION_PENDING_RESOLUTION",
            "PAPER_RECONCILIATION_FAILED",
        ],
        checks=checks,
        pending_resolutions=[],
        blockers=blockers,
        api_keys_loaded=False,
        private_keys_loaded=False,
        next_action="Evaluate live-market paper rehearsal readiness."
        if status == "PAPER_RECONCILIATION_PASSED"
        else "Fix paper ledger/reconciliation mismatch.",
    )


def write_live_market_paper_reconciliation_report(
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    payload = build_live_market_paper_reconciliation(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_reconciliation.json",
        md_name="latest_reconciliation.md",
        title="Live Market Paper Reconciliation",
        summary="Fake-money reconciliation across observer, intent, fill, ledger, position, and PnL state.",
    )
    _merge_state(output_root=output_root, fake_reconciliation_state=payload["status"])
    return payload


def _merge_state(*, output_root: str | Path, **updates: Any) -> None:
    path = Path(output_root) / STATE_JSON
    if not path.exists():
        return
    state = json.loads(path.read_text(encoding="utf-8"))
    state.update(updates)
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
