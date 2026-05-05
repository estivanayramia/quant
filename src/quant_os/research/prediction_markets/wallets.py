from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from quant_os.data.prediction_markets.schema import PredictionMarketRecord

WALLET_RESEARCH_SAFETY = {
    "copy_trading_enabled": False,
    "execution_authority": "NONE",
    "profitability_inference": "DISABLED",
}


def load_wallet_activity(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = "wallet activity fixture must contain a JSON object"
        raise ValueError(msg)
    return payload


def aggregate_wallet_activity(
    activity_payload: dict[str, Any],
    *,
    markets: list[PredictionMarketRecord] | None = None,
) -> dict[str, Any]:
    activities = sorted(
        [item for item in activity_payload.get("activities", []) if isinstance(item, dict)],
        key=lambda item: (str(item.get("timestamp", "")), str(item.get("wallet", ""))),
    )
    market_lookup = {market.market_id: market for market in markets or []}
    wallet_totals: dict[str, float] = defaultdict(float)
    wallet_markets: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    cluster_groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    total_notional = 0.0

    for item in activities:
        wallet = str(item.get("wallet") or "").lower()
        market_id = str(item.get("market_id") or "")
        outcome = str(item.get("outcome") or "").upper()
        side = str(item.get("side") or "").upper()
        notional = float(item.get("notional_usd") or 0.0)
        total_notional += notional
        wallet_totals[wallet] += notional
        wallet_markets[wallet][market_id] += notional
        cluster_groups[(market_id, outcome, side)].append(item)

    inferred_patterns = _specialization_patterns(wallet_totals, wallet_markets, market_lookup)
    inferred_patterns.extend(_coordination_patterns(cluster_groups))
    return {
        "source": activity_payload.get("source", "polymarket_wallet_activity"),
        "source_mode": activity_payload.get("source_mode", "fixture"),
        "captured_at": activity_payload.get("captured_at"),
        "observed_facts": {
            "wallet_count": len(wallet_totals),
            "activity_count": len(activities),
            "market_count": len({str(item.get("market_id") or "") for item in activities}),
            "total_notional_usd": round(total_notional, 6),
            "top_wallets_by_notional": [
                {"wallet": wallet, "notional_usd": round(notional, 6)}
                for wallet, notional in sorted(
                    wallet_totals.items(),
                    key=lambda pair: pair[1],
                    reverse=True,
                )
            ],
        },
        "inferred_patterns": inferred_patterns,
        "unknowns": [
            "profitability is not inferred from wallet activity; no causal alpha claim is made.",
            "Wallet ownership, hedges, off-platform positions, and intent are unknown.",
            "Clusters are leads for later investigation, not direct action signals.",
        ],
        "execution_authority": WALLET_RESEARCH_SAFETY["execution_authority"],
        "copy_trading_enabled": WALLET_RESEARCH_SAFETY["copy_trading_enabled"],
        "live_trading_enabled": False,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _specialization_patterns(
    wallet_totals: dict[str, float],
    wallet_markets: dict[str, dict[str, float]],
    market_lookup: dict[str, PredictionMarketRecord],
) -> list[dict[str, Any]]:
    patterns: list[dict[str, Any]] = []
    for wallet, total in wallet_totals.items():
        if total <= 0:
            continue
        market_id, market_notional = max(wallet_markets[wallet].items(), key=lambda pair: pair[1])
        concentration = market_notional / total
        if concentration >= 0.75:
            market = market_lookup.get(market_id)
            patterns.append(
                {
                    "label": "MARKET_SPECIALIZATION",
                    "wallet": wallet,
                    "market_id": market_id,
                    "category": market.category if market else None,
                    "concentration": round(concentration, 6),
                    "confidence_limit": "HEURISTIC_NOT_CAUSAL_ALPHA",
                }
            )
    return patterns


def _coordination_patterns(
    cluster_groups: dict[tuple[str, str, str], list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    patterns: list[dict[str, Any]] = []
    for (market_id, outcome, side), items in sorted(cluster_groups.items()):
        wallets = sorted({str(item.get("wallet") or "").lower() for item in items})
        if len(wallets) < 3:
            continue
        timestamps = sorted(str(item.get("timestamp") or "") for item in items)
        patterns.append(
            {
                "label": "POSSIBLE_COORDINATION_CLUSTER",
                "market_id": market_id,
                "outcome": outcome,
                "side": side,
                "wallet_count": len(wallets),
                "activity_count": len(items),
                "first_seen": timestamps[0],
                "last_seen": timestamps[-1],
                "time_span_minutes": _time_span_minutes(timestamps),
                "confidence_limit": "HEURISTIC_NOT_CERTAINTY",
            }
        )
    return patterns


def _time_span_minutes(timestamps: list[str]) -> float | None:
    if len(timestamps) < 2:
        return None
    try:
        start = datetime.fromisoformat(timestamps[0].replace("Z", "+00:00"))
        end = datetime.fromisoformat(timestamps[-1].replace("Z", "+00:00"))
    except ValueError:
        return None
    return round((end - start).total_seconds() / 60.0, 6)
