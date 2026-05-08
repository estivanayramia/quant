from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from quant_os.execution.shadow_order_intents import ShadowOrderIntent

SHADOW_RISK_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
    "prediction_market_execution_authority_added": False,
}


@dataclass(frozen=True)
class ShadowRiskLimits:
    max_concurrent_intents: int = 1
    max_intent_size: str = "5"
    min_intent_size: str = "1"
    per_market_exposure_cap: str = "5"
    lane_enabled: bool = True


def evaluate_shadow_risk(
    *,
    intent: ShadowOrderIntent,
    limits: ShadowRiskLimits | None = None,
    current_intent_count: int = 0,
    current_market_exposure: str = "0",
    replay_inputs_sufficient: bool = False,
) -> dict[str, Any]:
    active_limits = limits or ShadowRiskLimits()
    blockers = []
    if not replay_inputs_sufficient:
        blockers.append("KILL_STATE_REPLAY_INPUTS_INSUFFICIENT")
    if not active_limits.lane_enabled:
        blockers.append("LANE_BLOCKED")
    if current_intent_count >= active_limits.max_concurrent_intents:
        blockers.append("MAX_CONCURRENT_INTENTS")
    if _decimal(intent.intended_size) < _decimal(active_limits.min_intent_size):
        blockers.append("SIZE_TOO_SMALL")
    if _decimal(intent.intended_size) > _decimal(active_limits.max_intent_size):
        blockers.append("INTENT_SIZE_EXCEEDS_CAP")
    if (
        _decimal(current_market_exposure) + _decimal(intent.intended_size)
        > _decimal(active_limits.per_market_exposure_cap)
    ):
        blockers.append("PER_MARKET_EXPOSURE_CAP")
    return {
        "risk_status": "RISK_BLOCKED" if blockers else "RISK_ALLOWED_FOR_SHADOW_ONLY",
        "blocking_reasons": _dedupe(blockers),
        "limits": {
            "max_concurrent_intents": active_limits.max_concurrent_intents,
            "max_intent_size": active_limits.max_intent_size,
            "min_intent_size": active_limits.min_intent_size,
            "per_market_exposure_cap": active_limits.per_market_exposure_cap,
            "lane_enabled": active_limits.lane_enabled,
        },
        **SHADOW_RISK_SAFETY,
    }


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
