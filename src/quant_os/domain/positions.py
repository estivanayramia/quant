from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from quant_os.core.errors import DomainError
from quant_os.core.time import utc_now
from quant_os.domain.fills import Fill
from quant_os.domain.orders import OrderSide


class Position(BaseModel):
    symbol: str
    quantity: float = 0.0
    average_entry_price: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    opened_at: datetime | None = None
    updated_at: datetime = Field(default_factory=utc_now)

    @property
    def is_open(self) -> bool:
        return abs(self.quantity) > 1e-12

    def apply_fill(self, fill: Fill) -> None:
        if fill.side == OrderSide.BUY:
            self._apply_buy(fill)
        elif fill.side == OrderSide.SELL:
            self._apply_sell(fill)
        else:
            msg = f"unsupported fill side {fill.side}"
            raise DomainError(msg)
        self.updated_at = fill.filled_at

    def _apply_buy(self, fill: Fill) -> None:
        if self.quantity < -1e-12:
            msg = "short positions are not supported in Milestone 1"
            raise DomainError(msg)
        total_cost = self.average_entry_price * self.quantity + fill.price * fill.quantity
        new_quantity = self.quantity + fill.quantity
        self.quantity = new_quantity
        self.average_entry_price = total_cost / new_quantity if new_quantity else 0.0
        self.realized_pnl -= fill.fee
        if self.opened_at is None:
            self.opened_at = fill.filled_at

    def _apply_sell(self, fill: Fill) -> None:
        if fill.quantity > self.quantity + 1e-12:
            msg = "sell fill would create a short position"
            raise DomainError(msg)
        self.realized_pnl += (fill.price - self.average_entry_price) * fill.quantity - fill.fee
        self.quantity -= fill.quantity
        if abs(self.quantity) <= 1e-12:
            self.quantity = 0.0
            self.average_entry_price = 0.0
            self.opened_at = None
