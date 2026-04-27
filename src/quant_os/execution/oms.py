from __future__ import annotations

from quant_os.core.commands import CandidateOrder
from quant_os.core.events import EventType, make_event
from quant_os.core.ids import deterministic_client_order_id
from quant_os.domain.orders import Order, OrderSide, OrderStatus, OrderType
from quant_os.ports.event_store import EventStorePort


class OMS:
    def __init__(self, event_store: EventStorePort) -> None:
        self.event_store = event_store
        self.sequence = 0

    def create_order(self, candidate: CandidateOrder) -> Order:
        self.sequence += 1
        client_order_id = deterministic_client_order_id(
            candidate.strategy_id,
            candidate.symbol,
            candidate.side.upper(),
            candidate.created_at,
            self.sequence,
        )
        return Order(
            client_order_id=client_order_id,
            strategy_id=candidate.strategy_id,
            symbol=candidate.symbol,
            side=OrderSide(candidate.side.upper()),
            quantity=candidate.quantity,
            order_type=OrderType(candidate.order_type),
            limit_price=candidate.limit_price,
            stop_price=candidate.stop_price,
            created_at=candidate.created_at,
            updated_at=candidate.created_at,
        )

    def submit(self, order: Order) -> Order:
        order.transition_to(OrderStatus.SUBMITTED)
        self._append_order_event(EventType.ORDER_SUBMITTED, order)
        return order

    def accept(self, order: Order) -> Order:
        order.transition_to(OrderStatus.ACCEPTED)
        self._append_order_event(EventType.ORDER_ACCEPTED, order)
        return order

    def reject(self, order: Order, reasons: list[str]) -> Order:
        order.transition_to(OrderStatus.REJECTED)
        self._append_order_event(EventType.ORDER_REJECTED, order, {"reasons": reasons})
        return order

    def cancel(self, order: Order, reason: str) -> Order:
        order.transition_to(OrderStatus.CANCELLED)
        self._append_order_event(EventType.ORDER_CANCELLED, order, {"reason": reason})
        return order

    def mark_filled(self, order: Order) -> Order:
        order.transition_to(OrderStatus.FILLED)
        return order

    def _append_order_event(
        self,
        event_type: EventType,
        order: Order,
        extra: dict[str, object] | None = None,
    ) -> None:
        payload = {"order": order.model_dump(mode="json")}
        payload.update(extra or {})
        self.event_store.append(make_event(event_type, order.client_order_id, payload))
