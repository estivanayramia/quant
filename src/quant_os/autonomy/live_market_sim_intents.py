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

REPORT_DIR = Path("reports/live_market_sim_profitability/intents")


def build_live_market_sim_intents(*, output_root: str | Path = ".") -> dict[str, Any]:
    observer = load_json(
        "reports/live_market_sim_profitability/observer/latest_observer.json",
        output_root=output_root,
    ) or {}
    observation = observer.get("observation") or {}
    market = observation.get("market") or {}
    blockers: list[str] = []
    if observer.get("status") != "LIVE_PROFIT_OBSERVER_READY":
        status = "LIVE_SIM_INTENT_NO_TRADE"
        intent = None
    elif not observation.get("forecast_evidence_hash") or not observation.get("market_evidence_hash"):
        status = "LIVE_SIM_INTENT_BLOCKED"
        blockers.append("MISSING_EVIDENCE_HASH")
        intent = None
    else:
        limit_price = float(market.get("yes_ask") or 0.0) + 0.03
        status = "LIVE_SIM_INTENT_READY"
        intent = {
            "fake_client_order_id": f"lmsi_{hash_payload(observation, length=18)}",
            "observation_id": observation.get("observation_id"),
            "market_ticker": market.get("ticker"),
            "side": "yes",
            "action": "buy",
            "limit_price": round(limit_price, 6),
            "public_yes_ask": float(market.get("yes_ask") or 0.0),
            "fake_contracts": 1,
            "fake_max_exposure": round(limit_price, 6),
            "fake_money": True,
            "no_transmit": True,
            "dry_run_only": True,
            "order_transmission_enabled": False,
            "authenticated_requests_enabled": False,
            "request_signing_enabled": False,
            "contains_signed_headers": False,
            "contains_private_key_path": False,
            "contains_executable_submission_code": False,
            "forecast_evidence_hash": observation.get("forecast_evidence_hash"),
            "market_evidence_hash": observation.get("market_evidence_hash"),
            "evidence_hash": hash_payload(observation),
        }
    return sim_safety_payload(
        schema_version="live_market_sim_intents_v1",
        status=status,
        allowed_statuses=[
            "LIVE_SIM_INTENT_READY",
            "LIVE_SIM_INTENT_NO_TRADE",
            "LIVE_SIM_INTENT_BLOCKED",
        ],
        observation_id=observation.get("observation_id"),
        intent=intent,
        fake_money=True,
        no_transmit=True,
        dry_run_only=True,
        blockers=blockers,
        next_action="Run conservative fake fill model."
        if status == "LIVE_SIM_INTENT_READY"
        else "Record no-trade through fill, ledger, and readiness stages.",
    )


def write_live_market_sim_intents_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_live_market_sim_intents(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_intents.json",
        md_name="latest_intents.md",
        title="Live Market Sim Intents",
        summary="Fake-money no-transmit order intent. This stage cannot submit an order.",
    )
    if payload.get("intent"):
        write_state(output_root=output_root, intents=[payload["intent"]], next_action=payload["next_action"])
    else:
        write_state(output_root=output_root, next_action=payload["next_action"])
    return payload
