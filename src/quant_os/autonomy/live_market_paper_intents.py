from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from quant_os.readiness.canary_readiness_common import (
    load_gate_payload,
    safety_payload,
    write_json_markdown_report,
)

REPORT_DIR = Path("reports/live_market_paper_rehearsal/intents")
STATE_JSON = Path("reports/live_market_paper_rehearsal/state/latest_state.json")


def build_live_market_paper_intents(*, output_root: str | Path = ".") -> dict[str, Any]:
    observer = load_gate_payload(
        "reports/live_market_paper_rehearsal/observer/latest_observer.json",
        output_root=output_root,
    ) or {}
    observation = observer.get("observation") or {}
    market = observation.get("market") or {}
    blockers: list[str] = []
    if observer.get("status") != "LIVE_MARKET_OBSERVATION_READY":
        status = "PAPER_INTENT_NO_TRADE"
        intent = None
    elif not observation.get("market_evidence_hash") or not observation.get("forecast_evidence_hash"):
        status = "PAPER_INTENT_BLOCKED"
        blockers.append("MISSING_EVIDENCE_HASH")
        intent = None
    else:
        status = "PAPER_INTENT_READY"
        intent = {
            "fake_client_order_id": _fake_client_order_id(observation),
            "market_ticker": market.get("ticker"),
            "side": "yes",
            "action": "buy",
            "limit_price": float(market.get("yes_ask") or 0.0),
            "fake_contracts": 1,
            "fake_max_exposure": 1.0,
            "max_total_loss": 1.0,
            "forecast_evidence_hash": observation.get("forecast_evidence_hash"),
            "market_evidence_hash": observation.get("market_evidence_hash"),
            "reason_code": "LIVE_MARKET_PAPER_REHEARSAL_ELIGIBLE_MARKET",
            "dry_run_only": True,
            "no_send": True,
            "fake_money": True,
            "order_transmission_enabled": False,
            "authenticated_requests_enabled": False,
            "api_keys_loaded": False,
            "private_keys_loaded": False,
            "contains_signed_headers": False,
            "contains_private_key_path": False,
            "contains_executable_submission_code": False,
        }
    payload = safety_payload(
        schema_version="live_market_paper_intents_v1",
        status=status,
        allowed_statuses=["PAPER_INTENT_READY", "PAPER_INTENT_NO_TRADE", "PAPER_INTENT_BLOCKED"],
        observation_id=observation.get("observation_id"),
        observation_kind=observation.get("observation_kind"),
        intent=intent,
        dry_run_only=True,
        no_send=True,
        fake_money=True,
        blockers=blockers,
        api_keys_loaded=False,
        private_keys_loaded=False,
        next_action="Run conservative fake fill model."
        if status == "PAPER_INTENT_READY"
        else "Record no-trade in fake fill and ledger stages.",
    )
    return payload


def write_live_market_paper_intents_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_live_market_paper_intents(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_intents.json",
        md_name="latest_intents.md",
        title="Live Market Paper Intents",
        summary="Fake-money no-transmit intent report. This report cannot submit an order.",
    )
    _merge_state(
        output_root=output_root,
        no_transmit_intents_generated=1 if payload["status"] == "PAPER_INTENT_READY" else 0,
    )
    return payload


def _fake_client_order_id(observation: dict[str, Any]) -> str:
    raw = json.dumps(observation, sort_keys=True, default=str)
    return f"paper_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:18]}"


def _merge_state(*, output_root: str | Path, **updates: Any) -> None:
    path = Path(output_root) / STATE_JSON
    if not path.exists():
        return
    state = json.loads(path.read_text(encoding="utf-8"))
    state.update(updates)
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
