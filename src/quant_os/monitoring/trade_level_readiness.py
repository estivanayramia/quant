from __future__ import annotations

from typing import Any

from quant_os.monitoring.trade_level_divergence import check_trade_level_divergence


def trade_level_readiness_status() -> dict[str, Any]:
    divergence = check_trade_level_divergence(write=True)
    return {
        "status": divergence["status"],
        "trade_level_reconciliation_available": divergence["trade_level_comparison_available"],
        "live_promotion_status": "TINY_LIVE_BLOCKED",
        "live_eligible": False,
        "blockers": [
            "No multi-week dry-run evidence yet.",
            "No real exchange permission verification.",
            "No stoploss-on-exchange live canary test.",
            "No human live approval gate.",
            "No live-specific incident response runbook.",
        ],
        "warnings": divergence["warnings"],
        "failures": divergence["failures"],
    }
