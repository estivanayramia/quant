from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from quant_os.execution.shadow_order_intents import ShadowOrderIntent

SHADOW_POLICY_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
    "prediction_market_execution_authority_added": False,
}


def generate_shadow_order_intents(*, replay_design: dict[str, Any]) -> list[ShadowOrderIntent]:
    intents = []
    replay_partial = replay_design["replay_design_status"] != "READY_FOR_NARROW_REPLAY_DESIGN"
    for event in replay_design["event_timeline"]:
        if event["event_type"] != "orderbook_snapshot":
            continue
        raw = event["raw_event"]
        intended_size = "2"
        limit_price = raw["best_ask_price"]
        reasons = ["NO_EDGE_SIGNAL", "CONFIDENCE_TOO_WEAK"]
        if replay_partial:
            reasons.append("REPLAY_INPUT_INSUFFICIENT")
        if _spread_bps(raw) > Decimal("500"):
            reasons.append("SPREAD_TOO_WIDE")
        if _decimal(intended_size) < Decimal("1"):
            reasons.append("SIZE_TOO_SMALL")
        intent = ShadowOrderIntent(
            timestamp=event["timestamp"],
            lane_id=replay_design["selected_lane_id"],
            market_id=event["market_id"],
            token_id=event["token_id"],
            side="BUY",
            intended_size=intended_size,
            limit_price=limit_price,
            price_discipline="cross_best_ask_with_penalties",
            reason="fixture_replay_shape_only",
            signal_family="none_edge_not_established",
            metadata={"source_event_index": event["event_index"]},
        )
        intents.append(intent.blocked(reasons))
    if intents:
        return intents
    return [
        ShadowOrderIntent(
            timestamp=None,
            lane_id=replay_design["selected_lane_id"],
            market_id=None,
            token_id=None,
            side="NO_TRADE",
            intended_size="0",
            limit_price=None,
            price_discipline="none",
            reason="no_orderbook_snapshot",
            signal_family="none_edge_not_established",
        ).blocked(["REPLAY_INPUT_INSUFFICIENT"])
    ]


def _spread_bps(raw_event: dict[str, Any]) -> Decimal:
    if raw_event["best_bid_price"] is None or raw_event["best_ask_price"] is None:
        return Decimal("999999")
    bid = _decimal(raw_event["best_bid_price"])
    ask = _decimal(raw_event["best_ask_price"])
    midpoint = (bid + ask) / Decimal("2")
    if midpoint <= 0:
        return Decimal("999999")
    return ((ask - bid) / midpoint) * Decimal("10000")


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")
