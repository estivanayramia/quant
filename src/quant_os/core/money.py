from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def quantize_money(value: float | Decimal, places: str = "0.0001") -> Decimal:
    return Decimal(str(value)).quantize(Decimal(places), rounding=ROUND_HALF_UP)


def bps_to_decimal(bps: float) -> float:
    return float(bps) / 10_000.0
