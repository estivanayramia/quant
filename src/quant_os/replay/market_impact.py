from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class MarketImpactResult:
    price: float
    impact_bps: float


@dataclass(frozen=True)
class MarketImpactModel:
    impact_bps_per_capacity: float = 25.0
    passive_impact_multiplier: float = 0.35
    max_impact_bps: float = 35.0

    def apply(
        self,
        *,
        price: float,
        row: pd.Series | dict[str, Any],
        side: str,
        quantity: float,
        mode: str,
    ) -> MarketImpactResult:
        capacity_notional = _capacity_notional(row, price)
        order_notional = abs(float(quantity) * float(price))
        capacity_fraction = order_notional / max(capacity_notional, 1.0)
        impact_bps = min(self.max_impact_bps, capacity_fraction * self.impact_bps_per_capacity)
        if mode == "passive":
            impact_bps *= self.passive_impact_multiplier
        adjusted = _adjust_price(price, side, impact_bps)
        return MarketImpactResult(price=adjusted, impact_bps=float(impact_bps))


def _capacity_notional(row: pd.Series | dict[str, Any], price: float) -> float:
    top_of_book = row.get("top_of_book_notional")
    if top_of_book is not None and not pd.isna(top_of_book):
        return float(top_of_book)
    volume = row.get("volume", 0.0)
    if pd.isna(volume):
        return 0.0
    return abs(float(volume) * float(price))


def _adjust_price(price: float, side: str, penalty_bps: float) -> float:
    direction = 1.0 if side.upper() == "BUY" else -1.0
    return float(price) * (1.0 + direction * penalty_bps / 10_000.0)
