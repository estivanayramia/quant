from __future__ import annotations

from quant_os.live_canary.config import load_live_execution_config


def validate_symbol_allowed(symbol: str, allowed_symbols: list[str] | None = None) -> dict[str, object]:
    config = load_live_execution_config()
    allowed = allowed_symbols or list(config.get("allowed_symbols", ["BTC/USDT", "ETH/USDT"]))
    normalized = symbol.upper()
    blockers = [] if normalized in {item.upper() for item in allowed} else ["LIVE_SYMBOL_NOT_ALLOWED"]
    return {
        "status": "PASS" if not blockers else "FAIL",
        "symbol": normalized,
        "allowed_symbols": allowed,
        "blockers": blockers,
    }

