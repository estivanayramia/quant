from __future__ import annotations

import numpy as np
import pandas as pd

from quant_os.core.commands import CandidateOrder
from quant_os.features.technical import moving_average
from quant_os.risk.sizing import quantity_for_notional


def baseline_ma_candidates(
    frame: pd.DataFrame,
    strategy_id: str = "baseline_ma",
    notional: float = 20.0,
) -> list[CandidateOrder]:
    data = frame.sort_values("timestamp").copy()
    data["ma_fast"] = moving_average(data["close"], 5)
    data["ma_slow"] = moving_average(data["close"], 20)
    data["spread"] = data["ma_fast"] - data["ma_slow"]
    candidates: list[CandidateOrder] = []
    in_position = False
    for index in range(1, len(data)):
        previous = data.iloc[index - 1]
        current = data.iloc[index]
        crossed_up = previous["spread"] <= 0 and current["spread"] > 0
        crossed_down = previous["spread"] >= 0 and current["spread"] < 0
        side: str | None = None
        if crossed_up and not in_position:
            side = "BUY"
            in_position = True
        elif crossed_down and in_position:
            side = "SELL"
            in_position = False
        if side is not None:
            quantity = quantity_for_notional(notional, float(current["close"]))
            candidates.append(
                CandidateOrder(
                    strategy_id=strategy_id,
                    symbol=str(current["symbol"]),
                    side=side,
                    quantity=quantity,
                    current_price=float(current["close"]),
                    estimated_spread_bps=2.0,
                    estimated_slippage_bps=2.0,
                    created_at=pd.Timestamp(current["timestamp"]).to_pydatetime(),
                )
            )
    return candidates


def placebo_random_candidates(
    frame: pd.DataFrame,
    strategy_id: str = "placebo_random",
    notional: float = 20.0,
    seed: int = 7,
) -> list[CandidateOrder]:
    rng = np.random.default_rng(seed)
    data = frame.sort_values("timestamp").copy()
    candidates: list[CandidateOrder] = []
    in_position = False
    for _, row in data.iterrows():
        draw = rng.random()
        side: str | None = None
        if draw < 0.035 and not in_position:
            side = "BUY"
            in_position = True
        elif draw > 0.965 and in_position:
            side = "SELL"
            in_position = False
        if side is not None:
            price = float(row["close"])
            candidates.append(
                CandidateOrder(
                    strategy_id=strategy_id,
                    symbol=str(row["symbol"]),
                    side=side,
                    quantity=quantity_for_notional(notional, price),
                    current_price=price,
                    estimated_spread_bps=2.5,
                    estimated_slippage_bps=2.5,
                    created_at=pd.Timestamp(row["timestamp"]).to_pydatetime(),
                )
            )
    return candidates
