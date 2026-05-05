from __future__ import annotations

import pandas as pd


def classify_volatility_regime(volatility: pd.Series) -> pd.Series:
    low = volatility.quantile(0.35)
    high = volatility.quantile(0.75)
    regime = pd.Series("normal", index=volatility.index, dtype="object")
    regime.loc[volatility <= low] = "low"
    regime.loc[volatility >= high] = "high"
    return regime
