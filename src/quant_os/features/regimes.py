from __future__ import annotations

import pandas as pd

from quant_os.features.technical import volatility


def volatility_regime(close: pd.Series, window: int = 20) -> pd.Series:
    vol = volatility(close, window)
    threshold = vol.median()
    return vol.apply(lambda value: "high_vol" if value > threshold else "normal_vol")
