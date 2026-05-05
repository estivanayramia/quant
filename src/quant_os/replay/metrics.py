from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from quant_os.replay.fills import ReplayFill


def replay_metrics(
    fills: list[ReplayFill],
    equity_curve: list[float],
    *,
    starting_cash: float,
    turnover: float,
    bars: int,
) -> dict[str, Any]:
    equity = pd.Series(equity_curve, dtype="float64")
    returns = equity.pct_change().fillna(0.0)
    final_equity = float(equity.iloc[-1]) if not equity.empty else starting_cash
    trade_returns = _paired_trade_returns(fills)
    expectancy = float(np.mean(trade_returns) * 10_000.0) if trade_returns else 0.0
    drawdown = _max_drawdown(equity)
    sharpe = 0.0
    if returns.std() > 0:
        sharpe = float((returns.mean() / returns.std()) * math.sqrt(365 * 24 * 60))
    time_in_market = _time_in_market(fills, bars)
    return {
        "final_equity": final_equity,
        "total_return": final_equity / starting_cash - 1.0,
        "expectancy_after_costs": expectancy,
        "max_drawdown": drawdown,
        "sharpe_after_costs": sharpe,
        "trade_count": len(trade_returns),
        "turnover": float(turnover),
        "time_in_market": time_in_market,
        "capacity_approximation": float(turnover / max(1, len(fills))),
        "parameter_sensitivity": float(abs(expectancy) / (1.0 + abs(drawdown * 10_000.0))),
    }


def _paired_trade_returns(fills: list[ReplayFill]) -> list[float]:
    entries: dict[str, ReplayFill] = {}
    returns: list[float] = []
    for fill in fills:
        if fill.side == "BUY":
            entries[fill.symbol] = fill
        elif fill.side == "SELL" and fill.symbol in entries:
            entry = entries.pop(fill.symbol)
            returns.append((fill.price - entry.price) / entry.price)
    return returns


def _max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    peak = equity.cummax()
    drawdown = equity / peak - 1.0
    return float(drawdown.min())


def _time_in_market(fills: list[ReplayFill], bars: int) -> float:
    if bars <= 0 or not fills:
        return 0.0
    open_symbols: set[str] = set()
    exposure_events = 0
    for fill in fills:
        if fill.side == "BUY":
            open_symbols.add(fill.symbol)
        elif fill.side == "SELL":
            open_symbols.discard(fill.symbol)
        if open_symbols:
            exposure_events += 1
    return min(1.0, exposure_events / bars)
