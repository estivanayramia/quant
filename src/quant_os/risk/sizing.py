from __future__ import annotations


def quantity_for_notional(notional: float, price: float) -> float:
    if price <= 0:
        msg = "price must be positive"
        raise ValueError(msg)
    return notional / price
