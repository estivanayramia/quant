from __future__ import annotations

import numpy as np
import pandas as pd

from quant_os.features.technical import atr_like_range, returns


def add_volatility_features(frame: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    data = frame.sort_values(["symbol", "timestamp"]).copy()
    pieces = []
    for _, group in data.groupby("symbol", sort=False):
        group = group.copy()
        group["returns"] = returns(group["close"])
        group["log_returns"] = np.log(group["close"] / group["close"].shift(1)).fillna(0.0)
        group["rolling_volatility"] = (
            group["returns"].rolling(window=window, min_periods=2).std().fillna(0.0)
        )
        group["atr_like"] = atr_like_range(group)
        pieces.append(group)
    return pd.concat(pieces).sort_index()
