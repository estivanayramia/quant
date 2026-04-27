from __future__ import annotations

from quant_os.domain.orders import Order, OrderStatus


class OrderStateMachine:
    def transition(self, order: Order, status: OrderStatus) -> Order:
        order.transition_to(status)
        return order
