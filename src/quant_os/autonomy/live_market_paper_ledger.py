from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from quant_os.autonomy.live_market_paper_pnl import calculate_fake_pnl
from quant_os.readiness.canary_readiness_common import (
    load_gate_payload,
    safety_payload,
    write_json_markdown_report,
)

REPORT_DIR = Path("reports/live_market_paper_rehearsal/ledger")
STATE_JSON = Path("reports/live_market_paper_rehearsal/state/latest_state.json")


def build_live_market_paper_ledger(
    *,
    output_root: str | Path = ".",
    intents_payload: dict[str, Any] | None = None,
    fills_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    intents_payload = intents_payload or load_gate_payload(
        "reports/live_market_paper_rehearsal/intents/latest_intents.json",
        output_root=output_root,
    ) or {}
    fills_payload = fills_payload or load_gate_payload(
        "reports/live_market_paper_rehearsal/fills/latest_fake_fills.json",
        output_root=output_root,
    ) or {}
    intent = intents_payload.get("intent")
    fake_fill = fills_payload.get("fake_fill")
    events = _events_for(intent=intent, fake_fill=fake_fill, observation_id=intents_payload.get("observation_id"))
    keys = [event["idempotency_key"] for event in events]
    blockers = []
    if len(keys) != len(set(keys)):
        blockers.append("DUPLICATE_FAKE_LEDGER_EVENT")
    status = "PAPER_LEDGER_UPDATED" if not blockers else "PAPER_LEDGER_BLOCKED"
    contracts = int((fake_fill or {}).get("filled_contracts") or 0)
    fake_position = {
        "state": "OPEN_FAKE_POSITION" if contracts else "NO_POSITION",
        "market_ticker": (intent or {}).get("market_ticker"),
        "contracts": contracts,
        "max_loss": round(float((fake_fill or {}).get("fill_price") or 0.0) * contracts, 6),
        "fake_money": True,
    }
    fake_pnl = calculate_fake_pnl(intent=intent, fake_fill=fake_fill)
    return safety_payload(
        schema_version="live_market_paper_ledger_v1",
        status=status,
        allowed_statuses=[
            "PAPER_LEDGER_UPDATED",
            "PAPER_LEDGER_BLOCKED",
            "PAPER_POSITION_UNKNOWN_BLOCKED",
        ],
        observation_id=intents_payload.get("observation_id") or fills_payload.get("observation_id"),
        ledger_events=events,
        fake_position=fake_position,
        fake_pnl=fake_pnl,
        fake_fees={"assumption": "zero_fee_first_dollar_paper_rehearsal", "amount": 0.0},
        duplicate_fake_client_ids=False,
        blockers=blockers,
        api_keys_loaded=False,
        private_keys_loaded=False,
        next_action="Run fake reconciliation.",
    )


def write_live_market_paper_ledger_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_live_market_paper_ledger(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_paper_ledger.json",
        md_name="latest_paper_ledger.md",
        title="Live Market Paper Ledger",
        summary="Fake-money paper ledger with idempotent no-trade, no-fill, and fake-fill events.",
    )
    _merge_state(
        output_root=output_root,
        fake_position_state=payload["fake_position"]["state"],
        fake_pnl=payload["fake_pnl"],
    )
    return payload


def _events_for(
    *,
    intent: dict[str, Any] | None,
    fake_fill: dict[str, Any] | None,
    observation_id: str | None,
) -> list[dict[str, Any]]:
    base = _hash({"intent": intent, "fake_fill": fake_fill, "observation_id": observation_id})
    event_types = ["paper_observation", "paper_intent", "paper_fill", "paper_position", "paper_pnl"]
    events = []
    for index, event_type in enumerate(event_types):
        events.append(
            {
                "event_type": event_type,
                "idempotency_key": f"{base}-{index}",
                "observation_id": observation_id,
                "fake_client_order_id": (intent or {}).get("fake_client_order_id"),
                "fake_fill_id": (fake_fill or {}).get("fake_fill_id"),
                "evidence_hash": base,
                "fake_money": True,
                "no_send": True,
                "offline_only": True,
            }
        )
    return events


def _hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _merge_state(*, output_root: str | Path, **updates: Any) -> None:
    path = Path(output_root) / STATE_JSON
    if not path.exists():
        return
    state = json.loads(path.read_text(encoding="utf-8"))
    state.update(updates)
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
