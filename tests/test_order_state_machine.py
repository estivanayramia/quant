from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from quant_os.core.errors import InvalidOrderTransition
from quant_os.domain.orders import Order, OrderSide, OrderStatus


def _order() -> Order:
    return Order(
        client_order_id="co_test",
        strategy_id="s1",
        symbol="SPY",
        side=OrderSide.BUY,
        quantity=1.0,
    )


def test_valid_order_state_transitions_succeed():
    order = _order()
    order.transition_to(OrderStatus.SUBMITTED)
    order.transition_to(OrderStatus.ACCEPTED)
    order.transition_to(OrderStatus.FILLED)
    assert order.status == OrderStatus.FILLED


def test_invalid_order_state_transitions_fail():
    order = _order()
    with pytest.raises(InvalidOrderTransition):
        order.transition_to(OrderStatus.FILLED)


@given(status=st.sampled_from(list(OrderStatus)))
def test_terminal_order_states_reject_transitions(status: OrderStatus):
    if status not in {OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED}:
        return
    order = _order()
    order.status = status
    with pytest.raises(InvalidOrderTransition):
        order.transition_to(OrderStatus.SUBMITTED)
