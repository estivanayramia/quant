from __future__ import annotations

from typing import Any

from quant_os.integrations.freqtrade.trade_reconciliation import reconcile_freqtrade_trades


def check_trade_level_divergence(write: bool = True) -> dict[str, Any]:
    reconciliation = reconcile_freqtrade_trades(write=write)
    return {
        "generated_at": reconciliation["generated_at"],
        "status": reconciliation["status"],
        "trade_level_comparison_available": reconciliation["trade_level_comparison_available"],
        "failures": reconciliation["failures"],
        "warnings": reconciliation["warnings"],
        "live_trading_enabled": False,
        "dry_run_only": True,
    }
