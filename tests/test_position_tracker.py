from __future__ import annotations

from quant_os.domain.fills import Fill
from quant_os.domain.orders import OrderSide
from quant_os.domain.positions import Position


def test_pms_position_state_updates_from_fills():
    position = Position(symbol="SPY")
    position.apply_fill(
        Fill.from_order("co1", "s1", "SPY", OrderSide.BUY, quantity=2.0, price=10.0)
    )
    position.apply_fill(
        Fill.from_order("co2", "s1", "SPY", OrderSide.SELL, quantity=1.0, price=12.0)
    )
    assert position.quantity == 1.0
    assert position.realized_pnl == 2.0
