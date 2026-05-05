from __future__ import annotations

import pandas as pd


def estimate_capacity_from_liquidity(row: pd.Series, participation_rate: float = 0.02) -> float:
    price = float(row.get("close", row.get("price", 0.0)))
    volume = float(row.get("volume", 0.0))
    return max(0.0, price * volume * participation_rate)
