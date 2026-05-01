from __future__ import annotations

from quant_os.live_canary.exchange_port import ExchangeCapabilities
from quant_os.security.config_guard import GuardResult


def stoploss_exchange_guard(capabilities: ExchangeCapabilities | None = None) -> GuardResult:
    reasons: list[str] = []
    if capabilities is None:
        reasons.append("STOPLOSS_EXCHANGE_CAPABILITY_UNKNOWN")
    else:
        if capabilities.supports_stoploss_on_exchange is not True:
            reasons.append("STOPLOSS_ON_EXCHANGE_NOT_SUPPORTED")
        if capabilities.supports_margin:
            reasons.append("ADAPTER_MARGIN_CAPABILITY_ENABLED")
        if capabilities.supports_futures:
            reasons.append("ADAPTER_FUTURES_CAPABILITY_ENABLED")
        if capabilities.supports_leverage:
            reasons.append("ADAPTER_LEVERAGE_CAPABILITY_ENABLED")
        if capabilities.supports_shorting:
            reasons.append("ADAPTER_SHORTING_CAPABILITY_ENABLED")
    return GuardResult(
        passed=not reasons,
        reasons=reasons,
        details={
            "checked": "stoploss_exchange_guard",
            "capabilities": capabilities.__dict__ if capabilities else None,
            "live_promotion_status": "LIVE_BLOCKED",
        },
    )

