from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from quant_os.execution.shadow_order_intents import ShadowOrderIntent
from quant_os.replay.prediction_market_event_schema import (
    PredictionMarketReplayEvent,
    normalize_decimal,
)

FILL_MODEL_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
    "prediction_market_execution_authority_added": False,
}


@dataclass(frozen=True)
class ConservativeFillConfig:
    max_fill_fraction: str = "0.25"
    max_intent_size: str = "5"
    min_intent_size: str = "1"
    max_spread_bps: str = "600"
    latency_penalty_bps: str = "50"
    stale_book_penalty_bps: str = "75"
    allow_full_fill: bool = False
    allow_optimistic_queue: bool = False

    def __post_init__(self) -> None:
        if self.allow_full_fill or self.allow_optimistic_queue:
            raise ValueError("optimistic fill assumptions are not allowed")
        if _decimal(self.max_fill_fraction) > Decimal("0.5"):
            raise ValueError("optimistic fill fraction is not allowed")
        if _decimal(self.latency_penalty_bps) < 0 or _decimal(self.stale_book_penalty_bps) < 0:
            raise ValueError("optimistic negative penalties are not allowed")


def evaluate_conservative_fill(
    *,
    intent: ShadowOrderIntent,
    orderbook_event: PredictionMarketReplayEvent,
    config: ConservativeFillConfig | None = None,
) -> dict[str, Any]:
    active_config = config or ConservativeFillConfig()
    facts = _observed_facts(orderbook_event)
    assumptions = _assumptions(active_config)
    unknowns = [
        "queue_position_unknown",
        "hidden_liquidity_unknown",
        "fill_priority_unknown",
        "latency_distribution_unknown",
    ]
    blockers = _fill_blockers(intent=intent, orderbook_event=orderbook_event, config=active_config)
    if blockers:
        return {
            "fill_status": "NO_FILL_CONSERVATIVE",
            "filled_size": "0",
            "effective_price": None,
            "blocked_reasons": blockers,
            "observed_facts": facts,
            "deterministic_assumptions": assumptions,
            "unknowns": unknowns,
            **FILL_MODEL_SAFETY,
        }
    quote_price = _execution_quote(intent, orderbook_event)
    quote_size = _execution_quote_size(intent, orderbook_event)
    fill_cap = quote_size * _decimal(active_config.max_fill_fraction)
    filled_size = min(
        _decimal(intent.intended_size),
        fill_cap,
        _decimal(active_config.max_intent_size),
    )
    penalty_multiplier = Decimal("1") + (
        _decimal(active_config.latency_penalty_bps)
        + _decimal(active_config.stale_book_penalty_bps)
    ) / Decimal("10000")
    effective_price = quote_price * penalty_multiplier
    return {
        "fill_status": "PARTIAL_FILL_CONSERVATIVE" if filled_size > 0 else "NO_FILL_CONSERVATIVE",
        "filled_size": normalize_decimal(filled_size),
        "effective_price": normalize_decimal(effective_price),
        "blocked_reasons": [],
        "observed_facts": facts,
        "deterministic_assumptions": assumptions,
        "unknowns": unknowns,
        **FILL_MODEL_SAFETY,
    }


def _fill_blockers(
    *,
    intent: ShadowOrderIntent,
    orderbook_event: PredictionMarketReplayEvent,
    config: ConservativeFillConfig,
) -> list[str]:
    blockers = []
    if orderbook_event.event_type != "orderbook_snapshot":
        blockers.append("NO_ORDERBOOK_SNAPSHOT")
    if intent.side not in {"BUY", "SELL"}:
        blockers.append("UNSUPPORTED_SIDE")
    if _decimal(intent.intended_size) < _decimal(config.min_intent_size):
        blockers.append("SIZE_TOO_SMALL")
    if _spread_bps(orderbook_event) > _decimal(config.max_spread_bps):
        blockers.append("SPREAD_TOO_WIDE")
    if intent.side == "BUY":
        if orderbook_event.best_ask_price is None or orderbook_event.best_ask_size is None:
            blockers.append("ASK_SIDE_MISSING")
        elif intent.limit_price is None or _decimal(intent.limit_price) < _decimal(
            orderbook_event.best_ask_price
        ):
            blockers.append("LIMIT_NOT_MARKETABLE")
    if intent.side == "SELL":
        if orderbook_event.best_bid_price is None or orderbook_event.best_bid_size is None:
            blockers.append("BID_SIDE_MISSING")
        elif intent.limit_price is None or _decimal(intent.limit_price) > _decimal(
            orderbook_event.best_bid_price
        ):
            blockers.append("LIMIT_NOT_MARKETABLE")
    return _dedupe(blockers)


def _observed_facts(orderbook_event: PredictionMarketReplayEvent) -> dict[str, Any]:
    return {
        "event_type": orderbook_event.event_type,
        "timestamp": orderbook_event.timestamp,
        "best_bid_price": orderbook_event.best_bid_price,
        "best_bid_size": orderbook_event.best_bid_size,
        "best_ask_price": orderbook_event.best_ask_price,
        "best_ask_size": orderbook_event.best_ask_size,
    }


def _assumptions(config: ConservativeFillConfig) -> dict[str, str | bool]:
    return {
        "max_fill_fraction": config.max_fill_fraction,
        "max_intent_size": config.max_intent_size,
        "max_spread_bps": config.max_spread_bps,
        "latency_penalty_bps": config.latency_penalty_bps,
        "stale_book_penalty_bps": config.stale_book_penalty_bps,
        "allow_full_fill": config.allow_full_fill,
        "allow_optimistic_queue": config.allow_optimistic_queue,
    }


def _execution_quote(intent: ShadowOrderIntent, orderbook_event: PredictionMarketReplayEvent) -> Decimal:
    if intent.side == "BUY":
        return _decimal(orderbook_event.best_ask_price)
    return _decimal(orderbook_event.best_bid_price)


def _execution_quote_size(
    intent: ShadowOrderIntent,
    orderbook_event: PredictionMarketReplayEvent,
) -> Decimal:
    if intent.side == "BUY":
        return _decimal(orderbook_event.best_ask_size)
    return _decimal(orderbook_event.best_bid_size)


def _spread_bps(orderbook_event: PredictionMarketReplayEvent) -> Decimal:
    if orderbook_event.best_bid_price is None or orderbook_event.best_ask_price is None:
        return Decimal("999999")
    bid = _decimal(orderbook_event.best_bid_price)
    ask = _decimal(orderbook_event.best_ask_price)
    midpoint = (bid + ask) / Decimal("2")
    if midpoint <= 0:
        return Decimal("999999")
    return ((ask - bid) / midpoint) * Decimal("10000")


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    deduped = []
    for item in items:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped
