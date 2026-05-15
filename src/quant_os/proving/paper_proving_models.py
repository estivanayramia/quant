from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

PAPER_PROVING_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
    "order_placement_enabled": False,
    "order_cancellation_enabled": False,
    "prediction_market_execution_authority_added": False,
}

REQUIRED_WARNINGS = [
    "PAPER_ONLY_NOT_LIVE",
    "SIMULATED_FILLS_NOT_REAL_FILLS",
    "BACKTEST_NOT_PROOF",
    "COST_MODEL_ASSUMPTION",
    "SOURCE_QUALITY_LIMITATION",
    "NO_LIVE_AUTHORITY",
]

PAPER_PROVING_READY_FOR_SELECTED_LANE = "PAPER_PROVING_READY_FOR_SELECTED_LANE"
PAPER_PROFIT_DIAGNOSTIC_ONLY = "PAPER_PROFIT_DIAGNOSTIC_ONLY"
PAPER_PROFIT_BLOCKED_BY_SAMPLE = "PAPER_PROFIT_BLOCKED_BY_SAMPLE"
PAPER_PROFIT_BLOCKED_BY_BASELINE = "PAPER_PROFIT_BLOCKED_BY_BASELINE"
PAPER_PROFIT_BLOCKED_BY_PLACEBO = "PAPER_PROFIT_BLOCKED_BY_PLACEBO"
PAPER_PROFIT_BLOCKED_BY_COSTS = "PAPER_PROFIT_BLOCKED_BY_COSTS"
PAPER_PROFIT_BLOCKED_BY_FILLS = "PAPER_PROFIT_BLOCKED_BY_FILLS"
NO_PAPER_PROFIT_SIGNAL = "NO_PAPER_PROFIT_SIGNAL"
NO_TESTABLE_LANE_FOUND = "NO_TESTABLE_LANE_FOUND"

ALLOWED_READINESS_STATUSES = [
    PAPER_PROVING_READY_FOR_SELECTED_LANE,
    PAPER_PROFIT_DIAGNOSTIC_ONLY,
    PAPER_PROFIT_BLOCKED_BY_SAMPLE,
    PAPER_PROFIT_BLOCKED_BY_BASELINE,
    PAPER_PROFIT_BLOCKED_BY_PLACEBO,
    PAPER_PROFIT_BLOCKED_BY_COSTS,
    PAPER_PROFIT_BLOCKED_BY_FILLS,
    NO_PAPER_PROFIT_SIGNAL,
    NO_TESTABLE_LANE_FOUND,
]


def decimal_value(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


def decimal_ratio(numerator: Decimal, denominator: Decimal) -> str:
    if denominator == 0:
        return "0"
    return render_decimal(numerator / denominator)


def render_decimal(value: Decimal) -> str:
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered or "0"


def max_drawdown(equity_curve: list[Decimal]) -> str:
    if not equity_curve:
        return "0"
    peak = equity_curve[0]
    worst = Decimal("0")
    for value in equity_curve:
        peak = max(peak, value)
        if peak > 0:
            worst = min(worst, (value - peak) / peak)
    return render_decimal(worst)
