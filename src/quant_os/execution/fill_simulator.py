from __future__ import annotations

from quant_os.adapters.broker_simulated import SimulatedBroker
from quant_os.domain.fills import Fill
from quant_os.domain.orders import Order


def simulate_fill(order: Order, price: float, slippage_bps: float, fee_bps: float) -> Fill:
    return SimulatedBroker().simulate_fill(order, price, slippage_bps, fee_bps)
