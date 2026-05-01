from __future__ import annotations

from quant_os.live_canary.config import load_live_execution_config


def validate_notional_limit(notional_usd: float, cap: float | None = None) -> dict[str, object]:
    config = load_live_execution_config()
    max_notional = float(cap if cap is not None else config.get("max_order_notional_usd", 25))
    blockers: list[str] = []
    if notional_usd <= 0:
        blockers.append("LIVE_NOTIONAL_NOT_POSITIVE")
    if notional_usd > max_notional:
        blockers.append("LIVE_NOTIONAL_CAP_EXCEEDED")
    return {
        "status": "PASS" if not blockers else "FAIL",
        "notional_usd": notional_usd,
        "max_order_notional_usd": max_notional,
        "blockers": blockers,
    }

