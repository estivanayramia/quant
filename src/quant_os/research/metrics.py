from __future__ import annotations

import numpy as np
import pandas as pd

from quant_os.domain.fills import Fill
from quant_os.domain.orders import OrderSide
from quant_os.risk.drawdown import max_drawdown


def calculate_trade_returns(fills: list[Fill]) -> list[float]:
    returns: list[float] = []
    entry_price: float | None = None
    for fill in fills:
        if fill.side == OrderSide.BUY:
            entry_price = fill.price
        elif fill.side == OrderSide.SELL and entry_price:
            returns.append((fill.price - entry_price) / entry_price)
            entry_price = None
    return returns


def calculate_metrics(
    fills: list[Fill],
    equity_curve: pd.Series,
    starting_equity: float = 10_000.0,
) -> dict[str, float | int]:
    final_equity = float(equity_curve.iloc[-1]) if not equity_curve.empty else starting_equity
    trade_returns = calculate_trade_returns(fills)
    wins = [value for value in trade_returns if value > 0]
    losses = [value for value in trade_returns if value < 0]
    gross_profit = float(np.sum(wins)) if wins else 0.0
    gross_loss = abs(float(np.sum(losses))) if losses else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    return {
        "total_return": final_equity / starting_equity - 1.0,
        "max_drawdown": max_drawdown(equity_curve) if not equity_curve.empty else 0.0,
        "win_rate": len(wins) / len(trade_returns) if trade_returns else 0.0,
        "profit_factor": profit_factor,
        "number_of_trades": len(trade_returns),
        "average_trade_return": float(np.mean(trade_returns)) if trade_returns else 0.0,
        "final_equity": final_equity,
    }
