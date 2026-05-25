from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.autonomy.live_market_sim_common import (
    ACTIVE_POLICY_VERSION,
    hash_payload,
    load_json,
    load_state,
    sim_safety_payload,
    write_state,
)
from quant_os.readiness.canary_readiness_common import write_json_markdown_report

REPORT_DIR = Path("reports/live_market_sim_profitability/intents")
CONSERVATIVE_COST_PER_CONTRACT = 0.03


def build_live_market_sim_intents(*, output_root: str | Path = ".") -> dict[str, Any]:
    observer = load_json(
        "reports/live_market_sim_profitability/observer/latest_observer.json",
        output_root=output_root,
    ) or {}
    observation = observer.get("observation") or {}
    market = observation.get("market") or {}
    market_ticker = str(market.get("ticker") or "")
    blockers: list[str] = []
    if observer.get("status") != "LIVE_PROFIT_OBSERVER_READY":
        status = "LIVE_SIM_INTENT_NO_TRADE"
        intent = None
    elif not observation.get("forecast_evidence_hash") or not observation.get("market_evidence_hash"):
        status = "LIVE_SIM_INTENT_BLOCKED"
        blockers.append("MISSING_EVIDENCE_HASH")
        intent = None
    elif str(market.get("status") or "").lower() not in {"", "active", "open"}:
        status = "LIVE_SIM_INTENT_BLOCKED"
        blockers.append("MARKET_NOT_ACTIVE")
        intent = None
    elif _opposite_side_effectively_certain(market):
        status = "LIVE_SIM_INTENT_NO_TRADE"
        blockers.append("OPPOSITE_SIDE_EFFECTIVELY_CERTAIN")
        intent = None
    elif _ticker_already_exposed(output_root=output_root, market_ticker=market_ticker):
        status = "LIVE_SIM_INTENT_NO_TRADE"
        blockers.append("DUPLICATE_MARKET_TICKER_EXPOSURE")
        intent = None
    elif _expected_net_edge(market, observation.get("forecast_evidence") or {}) <= 0:
        status = "LIVE_SIM_INTENT_NO_TRADE"
        blockers.append("EXPECTED_EDGE_AFTER_COST_NOT_POSITIVE")
        intent = None
    else:
        expected_net_edge = _expected_net_edge(market, observation.get("forecast_evidence") or {})
        limit_price = float(market.get("yes_ask") or 0.0) + CONSERVATIVE_COST_PER_CONTRACT
        status = "LIVE_SIM_INTENT_READY"
        intent = {
            "fake_client_order_id": f"lmsi_{hash_payload(observation, length=18)}",
            "policy_version": ACTIVE_POLICY_VERSION,
            "expected_net_edge": round(expected_net_edge, 6),
            "observation_id": observation.get("observation_id"),
            "market_ticker": market_ticker,
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


def _opposite_side_effectively_certain(market: dict[str, Any]) -> bool:
    return float(market.get("no_bid") or 0.0) >= 0.98 and float(market.get("yes_ask") or 0.0) <= 0.02


def _expected_net_edge(market: dict[str, Any], forecast: dict[str, Any]) -> float:
    yes_ask = float(market.get("yes_ask") or 0.0)
    forecast_probability = 0.68 if forecast.get("bucket_match") else 0.50
    return forecast_probability - yes_ask - CONSERVATIVE_COST_PER_CONTRACT


def _ticker_already_exposed(*, output_root: str | Path, market_ticker: str) -> bool:
    if not market_ticker:
        return False
    state = load_state(output_root=output_root)
    for collection_name in ("intents", "fills", "ledger_entries", "outcomes"):
        for item in state.get(collection_name, []) or []:
            if str(item.get("market_ticker") or "") == market_ticker:
                return True
    return False
