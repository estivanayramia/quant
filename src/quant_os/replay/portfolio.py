from __future__ import annotations

from pydantic import BaseModel, Field

from quant_os.replay.fills import ReplayFill


class ReplayPosition(BaseModel):
    symbol: str
    quantity: float = 0.0
    average_price: float = 0.0
    realized_pnl: float = 0.0


class ReplayPortfolio(BaseModel):
    starting_cash: float = 10_000.0
    cash: float = 10_000.0
    positions: dict[str, ReplayPosition] = Field(default_factory=dict)
    turnover: float = 0.0

    def apply_fill(self, fill: ReplayFill) -> None:
        position = self.positions.setdefault(fill.symbol, ReplayPosition(symbol=fill.symbol))
        self.turnover += abs(fill.notional)
        if fill.side == "BUY":
            total_cost = position.average_price * position.quantity + fill.price * fill.quantity
            position.quantity += fill.quantity
            position.average_price = total_cost / position.quantity if position.quantity else 0.0
            self.cash -= fill.notional + fill.fee
        else:
            sell_quantity = min(fill.quantity, position.quantity)
            position.realized_pnl += (fill.price - position.average_price) * sell_quantity - fill.fee
            position.quantity -= sell_quantity
            self.cash += fill.price * sell_quantity - fill.fee
            if abs(position.quantity) <= 1e-12:
                self.positions.pop(fill.symbol, None)

    def mark_to_market(self, prices: dict[str, float]) -> float:
        marked = sum(
            position.quantity * prices.get(symbol, position.average_price)
            for symbol, position in self.positions.items()
        )
        return self.cash + marked
