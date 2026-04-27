from __future__ import annotations

from typing import Protocol

from quant_os.domain.fills import Fill
from quant_os.domain.orders import Order


class BrokerPort(Protocol):
    def submit(self, order: Order) -> Order: ...

    def simulate_fill(
        self, order: Order, price: float, slippage_bps: float, fee_bps: float
    ) -> Fill: ...
