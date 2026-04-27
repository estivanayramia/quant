from __future__ import annotations

from quant_os.core.money import bps_to_decimal
from quant_os.domain.fills import Fill
from quant_os.domain.orders import Order, OrderSide, OrderStatus


class SimulatedBroker:
    """Deterministic broker simulator. It never connects to a live endpoint."""

    def submit(self, order: Order) -> Order:
        if order.status == OrderStatus.SUBMITTED:
            order.transition_to(OrderStatus.ACCEPTED)
        return order

    def simulate_fill(
        self, order: Order, price: float, slippage_bps: float, fee_bps: float
    ) -> Fill:
        direction = 1 if order.side == OrderSide.BUY else -1
        fill_price = price * (1 + direction * bps_to_decimal(slippage_bps))
        fee = abs(order.quantity * fill_price) * bps_to_decimal(fee_bps)
        return Fill.from_order(
            client_order_id=order.client_order_id,
            strategy_id=order.strategy_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=fill_price,
            fee=fee,
            slippage_bps=slippage_bps,
            filled_at=order.updated_at,
        )
