from __future__ import annotations

from pydantic import BaseModel, Field

from quant_os.domain.fills import Fill
from quant_os.domain.positions import Position


class PortfolioState(BaseModel):
    starting_cash: float = 10_000.0
    cash: float = 10_000.0
    positions: dict[str, Position] = Field(default_factory=dict)

    def apply_fill(self, fill: Fill) -> Position:
        position = self.positions.setdefault(fill.symbol, Position(symbol=fill.symbol))
        signed_cash = (
            -fill.quantity * fill.price if fill.side == "BUY" else fill.quantity * fill.price
        )
        self.cash += signed_cash - fill.fee
        position.apply_fill(fill)
        if not position.is_open:
            self.positions.pop(fill.symbol, None)
        return position

    @property
    def open_position_count(self) -> int:
        return len(self.positions)

    def position_notional(self, symbol: str, price: float) -> float:
        position = self.positions.get(symbol)
        return 0.0 if position is None else abs(position.quantity * price)
