from __future__ import annotations


def bps_to_decimal(value: float) -> float:
    return value / 10_000.0


def fee_for_notional(notional: float, fee_bps: float) -> float:
    return abs(notional) * bps_to_decimal(fee_bps)


def slippage_price(price: float, side: str, slippage_bps: float) -> float:
    direction = 1.0 if side.upper() == "BUY" else -1.0
    return price * (1.0 + direction * bps_to_decimal(slippage_bps))
