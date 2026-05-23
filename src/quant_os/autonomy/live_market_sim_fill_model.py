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

REPORT_DIR = Path("reports/live_market_sim_profitability/fills")


def apply_live_market_sim_fill_model(
    *,
    intent: dict[str, Any] | None,
    observation: dict[str, Any] | None,
    max_spread: float = 0.05,
) -> dict[str, Any]:
    blockers: list[str] = []
    market = (observation or {}).get("market") or {}
    yes_ask = float(market.get("yes_ask") or 0.0)
    spread = float(market.get("spread") or 0.0)
    liquidity = float(market.get("liquidity") or 0.0)
    if not intent:
        status = "LIVE_SIM_NO_FILL"
        fill = None
    elif not market.get("orderbook_available"):
        status = "LIVE_SIM_FILL_BLOCKED"
        blockers.append("ORDERBOOK_PUBLIC_DATA_MISSING")
        fill = None
    elif spread > max_spread:
        status = "LIVE_SIM_FILL_BLOCKED"
        blockers.append("SPREAD_TOO_WIDE")
        fill = None
    elif yes_ask <= 0.0 or float(intent.get("limit_price") or 0.0) < yes_ask:
        status = "LIVE_SIM_NO_FILL"
        fill = None
    else:
        filled_contracts = min(int(intent.get("fake_contracts") or 1), max(int(liquidity // 2), 1))
        filled_contracts = min(filled_contracts, 1)
        fill = {
            "fake_fill_id": f"lmsf_{hash_payload({'intent': intent, 'observation': observation})}",
            "observation_id": (observation or {}).get("observation_id"),
            "fake_client_order_id": intent.get("fake_client_order_id"),
            "market_ticker": intent.get("market_ticker"),
            "filled_contracts": filled_contracts,
            "fill_price": yes_ask,
            "public_book_yes_ask": yes_ask,
            "latency_penalty": 0.01,
            "adverse_selection_stress": 0.02,
            "fee_assumption": 0.0,
            "conservative_partial_fill": filled_contracts < int(intent.get("fake_contracts") or 1),
            "evidence_hash": hash_payload({"intent": intent, "market": market}),
        }
        status = "LIVE_SIM_FILL_APPLIED" if filled_contracts else "LIVE_SIM_NO_FILL"
    return sim_safety_payload(
        schema_version="live_market_sim_fill_v1",
        status=status,
        allowed_statuses=["LIVE_SIM_FILL_APPLIED", "LIVE_SIM_NO_FILL", "LIVE_SIM_FILL_BLOCKED"],
        observation_id=(observation or {}).get("observation_id"),
        fake_fill=fill,
        guaranteed_fill=False,
        fill_model="conservative_public_book_no_better_than_ask_with_latency_and_adverse_stress",
        blockers=blockers,
        next_action="Update fake ledger.",
    )


def build_live_market_sim_fill(*, output_root: str | Path = ".") -> dict[str, Any]:
    intents = load_json(
        "reports/live_market_sim_profitability/intents/latest_intents.json",
        output_root=output_root,
    ) or {}
    observer = load_json(
        "reports/live_market_sim_profitability/observer/latest_observer.json",
        output_root=output_root,
    ) or {}
    return apply_live_market_sim_fill_model(
        intent=intents.get("intent"),
        observation=observer.get("observation"),
    )


def write_live_market_sim_fill_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_live_market_sim_fill(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_fills.json",
        md_name="latest_fills.md",
        title="Live Market Sim Fill",
        summary="Conservative fake fill/no-fill model using only public book evidence.",
    )
    if payload.get("fake_fill"):
        write_state(output_root=output_root, fills=[payload["fake_fill"]], next_action=payload["next_action"])
    else:
        no_fill = {"observation_id": payload.get("observation_id"), "status": payload["status"]}
        write_state(output_root=output_root, no_fills=[no_fill], current_blockers=payload.get("blockers", []))
    return payload
