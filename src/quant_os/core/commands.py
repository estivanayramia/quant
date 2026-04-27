from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from quant_os.core.time import utc_now


class CandidateOrder(BaseModel):
    strategy_id: str
    symbol: str
    side: str
    quantity: float
    order_type: str = "market"
    limit_price: float | None = None
    stop_price: float | None = None
    current_price: float
    estimated_spread_bps: float = 0.0
    estimated_slippage_bps: float = 0.0
    asset_class: str = "spot"
    live_requested: bool = False
    no_trade: bool = False
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("quantity", "current_price")
    @classmethod
    def positive(cls, value: float) -> float:
        if value <= 0:
            msg = "quantity and current_price must be positive"
            raise ValueError(msg)
        return value

    @property
    def notional(self) -> float:
        return self.quantity * self.current_price
