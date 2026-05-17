from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.readiness.canary_readiness_common import safety_payload, write_json_markdown_report

REPORT_DIR = Path("reports/autonomous_live_fire_drill/ledger")


def build_fake_ledger(
    *,
    output_root: str | Path = ".",
    events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    events = events if events is not None else _default_events(output_root)
    event_ids = [event.get("event_id") for event in events]
    blockers = []
    if len(event_ids) != len(set(event_ids)):
        blockers.append("DUPLICATE_FAKE_LEDGER_EVENT")
    return safety_payload(
        schema_version="autonomous_fake_ledger_v1",
        status="FAKE_LEDGER_BLOCKED" if blockers else "FAKE_LEDGER_PASSED",
        allowed_statuses=["FAKE_LEDGER_PASSED", "FAKE_LEDGER_BLOCKED"],
        events=events,
        fake_positions=[event.get("position") for event in events if event.get("position")],
        fake_pnl={"realized_pnl": 0.0, "mark_to_market_pnl": 0.0},
        blockers=blockers,
        request_signing_enabled=False,
        api_keys_loaded=False,
        private_keys_loaded=False,
        next_action="Run fake reconciliation.",
    )


def write_fake_ledger_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_fake_ledger(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_ledger.json",
        md_name="latest_ledger.md",
        title="Autonomous Fake Ledger",
        summary="Idempotent fake-money ledger for fire-drill events.",
    )
    return payload


def _default_events(output_root: str | Path) -> list[dict[str, Any]]:
    path = Path(output_root) / "reports/autonomous_live_fire_drill/fake_execution/latest_fake_execution.json"
    if not path.exists():
        return [{"event_id": "no_trade", "evidence_hash": "no_trade_hash"}]
    execution = json.loads(path.read_text(encoding="utf-8"))
    return [
        {"event_id": "watcher", "evidence_hash": "watcher_hash"},
        {"event_id": "decision", "evidence_hash": "decision_hash"},
        {"event_id": "intent", "evidence_hash": "intent_hash"},
        {"event_id": "venue", "evidence_hash": "venue_hash", "position": execution.get("fake_positions", [])},
        {"event_id": "pnl", "evidence_hash": "pnl_hash"},
    ]
