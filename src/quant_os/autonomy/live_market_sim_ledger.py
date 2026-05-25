from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.autonomy.live_market_sim_common import (
    hash_payload,
    load_json,
    sim_safety_payload,
    write_state,
)
from quant_os.readiness.canary_readiness_common import write_json_markdown_report

REPORT_DIR = Path("reports/live_market_sim_profitability/ledger")


def build_live_market_sim_ledger(
    *,
    output_root: str | Path = ".",
    intents_payload: dict[str, Any] | None = None,
    fills_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    intents_payload = intents_payload or load_json(
        "reports/live_market_sim_profitability/intents/latest_intents.json",
        output_root=output_root,
    ) or {}
    fills_payload = fills_payload or load_json(
        "reports/live_market_sim_profitability/fills/latest_fills.json",
        output_root=output_root,
    ) or {}
    observer = load_json(
        "reports/live_market_sim_profitability/observer/latest_observer.json",
        output_root=output_root,
    ) or {}
    observation = observer.get("observation") or {}
    intent = intents_payload.get("intent")
    fill = fills_payload.get("fake_fill")
    entries = []
    blockers = []
    if intent and fill:
        entry = {
            "ledger_entry_id": f"lmsl_{hash_payload({'intent': intent, 'fill': fill})}",
            "observation_id": observation.get("observation_id") or intent.get("observation_id"),
            "market_ticker": intent.get("market_ticker"),
            "forecast_evidence_hash": intent.get("forecast_evidence_hash"),
            "market_evidence_hash": intent.get("market_evidence_hash"),
            "fake_client_order_id": intent.get("fake_client_order_id"),
            "fake_fill_id": fill.get("fake_fill_id"),
            "fake_entry_price": fill.get("fill_price"),
            "fake_contracts": fill.get("filled_contracts"),
            "fake_exposure": round(float(fill.get("fill_price") or 0.0) * int(fill.get("filled_contracts") or 0), 6),
            "fake_cost_assumptions": {
                "latency_penalty": fill.get("latency_penalty", 0.0),
                "adverse_selection_stress": fill.get("adverse_selection_stress", 0.0),
                "fee_assumption": fill.get("fee_assumption", 0.0),
            },
            "position_state": "OPEN_FAKE_POSITION",
            "outcome_status": "PENDING",
            "outcome_label": None,
            "event_hash": hash_payload({"intent": intent, "fill": fill, "observation": observation}),
            "fake_money": True,
            "no_transmit": True,
        }
        if not entry["forecast_evidence_hash"] or not entry["market_evidence_hash"]:
            blockers.append("MISSING_EVIDENCE_HASH")
        entries.append(entry)
    status = "LIVE_SIM_LEDGER_UPDATED" if not blockers else "LIVE_SIM_LEDGER_BLOCKED"
    return sim_safety_payload(
        schema_version="live_market_sim_ledger_v1",
        status=status,
        allowed_statuses=["LIVE_SIM_LEDGER_UPDATED", "LIVE_SIM_LEDGER_BLOCKED"],
        observation_id=observation.get("observation_id") or intents_payload.get("observation_id"),
        ledger_entries=entries,
        fake_position={
            "state": "OPEN_FAKE_POSITION" if entries else "NO_POSITION",
            "contracts": sum(int(item.get("fake_contracts") or 0) for item in entries),
            "fake_money": True,
        },
        blockers=blockers,
        next_action="Check public outcome labels for pending fake positions.",
    )


def write_live_market_sim_ledger_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_live_market_sim_ledger(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_ledger.json",
        md_name="latest_ledger.md",
        title="Live Market Sim Ledger",
        summary="Fake-money ledger across observation, intent, fill, position, and pending settlement.",
    )
    write_state(output_root=output_root, ledger_entries=payload["ledger_entries"], next_action=payload["next_action"])
    return payload
