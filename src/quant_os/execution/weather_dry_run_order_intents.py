from __future__ import annotations

from hashlib import sha256
from typing import Any


def build_weather_order_intent_previews(
    rows: list[dict[str, Any]],
    paper_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    decisions = {item.get("market_id"): item for item in paper_payload.get("paper_intents", []) or []}
    previews = []
    for index, row in enumerate(rows):
        decision = decisions.get(row.get("market_id"), {"intent": "NO_TRADE"})
        intent = str(decision.get("intent"))
        if intent == "NO_TRADE":
            continue
        evidence_hash = str(row.get("provenance_hash") or "")
        side = "yes" if intent == "BUY_YES" else "no"
        raw_client_id = f"weather-canary-{row.get('market_id')}-{index}"
        previews.append(
            {
                "market_ticker": row.get("market_id"),
                "side": side,
                "action": "buy",
                "limit_price": row.get("market_price", 0),
                "max_contracts": 1,
                "max_nominal_exposure": 1.0,
                "reason_code": "WEATHER_FORECAST_MARKET_MISMATCH",
                "source_evidence_hash": evidence_hash,
                "risk_decision": "ALLOW_PREVIEW_ONLY" if evidence_hash else "BLOCK_MISSING_EVIDENCE",
                "client_order_id_preview": sha256(raw_client_id.encode("utf-8")).hexdigest()[:24],
                "no_send": True,
                "live_trading_enabled": False,
                "execution_authority": "NONE",
            }
        )
    return previews
