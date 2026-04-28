from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from quant_os.core.commands import CandidateOrder
from quant_os.features.feature_store_local import build_feature_frame
from quant_os.risk.sizing import quantity_for_notional


@dataclass(frozen=True)
class StrategySpec:
    strategy_id: str
    name: str
    parameter_count: int
    description: str


STRATEGY_SPECS = {
    "baseline_momentum": StrategySpec(
        "baseline_momentum", "BaselineMomentumStrategy", 2, "Moving-average momentum baseline."
    ),
    "mean_reversion": StrategySpec(
        "mean_reversion", "MeanReversionStrategy", 3, "Discount/premium mean reversion candidate."
    ),
    "breakout": StrategySpec("breakout", "BreakoutStrategy", 3, "Rolling high breakout candidate."),
    "smc_structure": StrategySpec(
        "smc_structure",
        "SMCStructureStrategy",
        5,
        "Market-structure score candidate; no edge assumed.",
    ),
    "liquidity_sweep_reversal": StrategySpec(
        "liquidity_sweep_reversal",
        "LiquiditySweepReversalStrategy",
        4,
        "Liquidity sweep reversal candidate.",
    ),
    "no_trade": StrategySpec(
        "no_trade", "NoTradeStrategy", 0, "Negative control that emits no orders."
    ),
    "random_placebo": StrategySpec(
        "random_placebo", "RandomPlaceboStrategy", 1, "Seeded placebo/random strategy."
    ),
}


def available_strategy_specs() -> list[StrategySpec]:
    return list(STRATEGY_SPECS.values())


def candidate_orders_for_strategy(
    frame: pd.DataFrame,
    strategy: str,
    strategy_id: str | None = None,
    notional: float = 20.0,
    seed: int = 42,
) -> list[CandidateOrder]:
    strategy_id = strategy_id or strategy
    if strategy == "no_trade":
        return []
    if strategy == "random_placebo":
        return _random_placebo(frame, strategy_id, notional, seed)
    data = build_feature_frame(frame)
    if strategy == "baseline_momentum":
        signals = (data["ma_fast"] > data["ma_slow"]) & (
            data["ma_fast"].shift(1) <= data["ma_slow"].shift(1)
        )
        exits = (data["ma_fast"] < data["ma_slow"]) & (
            data["ma_fast"].shift(1) >= data["ma_slow"].shift(1)
        )
    elif strategy == "mean_reversion":
        signals = (data["premium_discount"] < 0.25) & (data["returns"] < 0)
        exits = data["premium_discount"] > 0.55
    elif strategy == "breakout":
        signals = data["breakout_above_rolling_high"].fillna(False)
        exits = data["breakdown_below_rolling_low"].fillna(False)
    elif strategy == "smc_structure":
        signals = data["smc_score"] > 0.45
        exits = data["smc_score"] < -0.15
    elif strategy == "liquidity_sweep_reversal":
        signals = data["liquidity_sweep_down"].fillna(False)
        exits = data["liquidity_sweep_up"].fillna(False)
    else:
        msg = f"unknown research strategy {strategy}"
        raise ValueError(msg)
    return _signals_to_candidates(data, signals, exits, strategy_id, notional)


def _signals_to_candidates(
    data: pd.DataFrame,
    entries: pd.Series,
    exits: pd.Series,
    strategy_id: str,
    notional: float,
) -> list[CandidateOrder]:
    candidates: list[CandidateOrder] = []
    in_position_by_symbol: dict[str, bool] = {}
    for index, row in data.iterrows():
        symbol = str(row["symbol"])
        in_position = in_position_by_symbol.get(symbol, False)
        side = None
        if bool(entries.loc[index]) and not in_position:
            side = "BUY"
            in_position_by_symbol[symbol] = True
        elif bool(exits.loc[index]) and in_position:
            side = "SELL"
            in_position_by_symbol[symbol] = False
        if side:
            price = float(row["close"])
            candidates.append(
                CandidateOrder(
                    strategy_id=strategy_id,
                    symbol=symbol,
                    side=side,
                    quantity=quantity_for_notional(notional, price),
                    current_price=price,
                    estimated_spread_bps=2.0,
                    estimated_slippage_bps=2.0,
                    created_at=pd.Timestamp(row["timestamp"]).to_pydatetime(),
                )
            )
    return candidates


def _random_placebo(
    frame: pd.DataFrame,
    strategy_id: str,
    notional: float,
    seed: int,
) -> list[CandidateOrder]:
    rng = np.random.default_rng(seed)
    data = frame.sort_values(["symbol", "timestamp"]).copy()
    candidates: list[CandidateOrder] = []
    in_position_by_symbol: dict[str, bool] = {}
    for _, row in data.iterrows():
        symbol = str(row["symbol"])
        draw = rng.random()
        side = None
        if draw < 0.03 and not in_position_by_symbol.get(symbol, False):
            side = "BUY"
            in_position_by_symbol[symbol] = True
        elif draw > 0.97 and in_position_by_symbol.get(symbol, False):
            side = "SELL"
            in_position_by_symbol[symbol] = False
        if side:
            price = float(row["close"])
            candidates.append(
                CandidateOrder(
                    strategy_id=strategy_id,
                    symbol=symbol,
                    side=side,
                    quantity=quantity_for_notional(notional, price),
                    current_price=price,
                    estimated_spread_bps=2.5,
                    estimated_slippage_bps=2.5,
                    created_at=pd.Timestamp(row["timestamp"]).to_pydatetime(),
                )
            )
    return candidates
