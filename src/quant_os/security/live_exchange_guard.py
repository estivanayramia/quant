from __future__ import annotations

from quant_os.live_canary.config import live_execution_safety_blockers, load_live_execution_config
from quant_os.security.config_guard import GuardResult


def live_exchange_guard() -> GuardResult:
    config = load_live_execution_config()
    reasons = live_execution_safety_blockers(config)
    if config.get("enabled") is not True:
        reasons.append("LIVE_EXECUTION_CONFIG_DISABLED")
    if config.get("exchange_adapter_enabled") is not True:
        reasons.append("LIVE_EXCHANGE_ADAPTER_DISABLED")
    if config.get("live_trading_allowed") is True:
        reasons.append("LIVE_TRADING_ALLOWED_TRUE_IN_LIVE_EXECUTION_CONFIG")
    execution = config.get("execution", {})
    if execution.get("live_order_enabled") is not True:
        reasons.append("LIVE_ORDER_ENABLED_FALSE")
    return GuardResult(
        passed=not reasons,
        reasons=sorted(set(reasons)),
        details={
            "checked": "live_exchange_guard",
            "live_promotion_status": "LIVE_BLOCKED",
            "allowed_symbols": config.get("allowed_symbols", []),
            "max_order_notional_usd": config.get("max_order_notional_usd"),
        },
    )

