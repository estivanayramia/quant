from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from quant_os.core.ids import new_fill_id
from quant_os.core.time import utc_now
from quant_os.domain.orders import OrderSide


class Fill(BaseModel):
    fill_id: str
    client_order_id: str
    strategy_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    fee: float = 0.0
    slippage_bps: float = 0.0
    filled_at: datetime = Field(default_factory=utc_now)

    @classmethod
    def from_order(
        cls,
        client_order_id: str,
        strategy_id: str,
        symbol: str,
        side: OrderSide,
        quantity: float,
        price: float,
        sequence: int = 1,
        fee: float = 0.0,
        slippage_bps: float = 0.0,
        filled_at: datetime | None = None,
    ) -> Fill:
        return cls(
            fill_id=new_fill_id(client_order_id, sequence),
            client_order_id=client_order_id,
            strategy_id=strategy_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            fee=fee,
            slippage_bps=slippage_bps,
            filled_at=filled_at or utc_now(),
        )
