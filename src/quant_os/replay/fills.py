from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
from pydantic import BaseModel

from quant_os.replay.costs import fee_for_notional, slippage_price


class FillAssumption(BaseModel):
    fill_ratio: float = 1.0
    fee_bps: float = 1.0
    slippage_bps: float = 1.0
    passive_price_improvement_bps: float = 1.0


class ReplayFill(BaseModel):
    strategy_id: str
    symbol: str
    side: str
    quantity: float
    remaining_quantity: float
    price: float
    fee: float
    liquidity: str
    timestamp: datetime

    @property
    def notional(self) -> float:
        return self.quantity * self.price


def apply_partial_fill(
    intent: Any,
    *,
    price: float,
    assumption: FillAssumption,
    liquidity: str = "aggressive",
    timestamp: pd.Timestamp | None = None,
) -> ReplayFill:
    fill_ratio = max(0.0, min(1.0, assumption.fill_ratio))
    quantity = float(intent.quantity) * fill_ratio
    remaining = float(intent.quantity) - quantity
    fill_price = slippage_price(price, str(intent.side), assumption.slippage_bps)
    if liquidity == "passive":
        direction = -1.0 if str(intent.side).upper() == "BUY" else 1.0
        fill_price *= 1.0 + direction * (assumption.passive_price_improvement_bps / 10_000.0)
    fee = fee_for_notional(quantity * fill_price, assumption.fee_bps)
    return ReplayFill(
        strategy_id=str(intent.strategy_id),
        symbol=str(intent.symbol),
        side=str(intent.side).upper(),
        quantity=quantity,
        remaining_quantity=remaining,
        price=float(fill_price),
        fee=float(fee),
        liquidity=liquidity,
        timestamp=pd.Timestamp(timestamp or intent.timestamp).to_pydatetime(),
    )
