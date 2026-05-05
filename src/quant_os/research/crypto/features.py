from __future__ import annotations

import numpy as np
import pandas as pd

from quant_os.data.normalization import normalize_dataset_frame
from quant_os.data.schemas import DatasetKind
from quant_os.research.crypto.regimes import classify_volatility_regime


def build_crypto_features(frame: pd.DataFrame) -> pd.DataFrame:
    data = normalize_dataset_frame(frame, DatasetKind.CANDLE)
    pieces = []
    for _, group in data.groupby("symbol", sort=False):
        group = group.sort_values("timestamp").copy()
        group["returns"] = group["close"].pct_change().fillna(0.0)
        group["rolling_volatility"] = group["returns"].rolling(20, min_periods=2).std().fillna(0.0)
        group["volatility_regime"] = classify_volatility_regime(group["rolling_volatility"])
        group["spread_bps"] = group.get("spread_bps", 2.0)
        group["volume_ma"] = group["volume"].rolling(30, min_periods=1).mean()
        max_volume = group["volume_ma"].rolling(60, min_periods=1).max().replace(0, np.nan)
        group["liquidity_score"] = (group["volume_ma"] / max_volume).fillna(0.0).clip(0.0, 1.0)
        price_range = (group["high"] - group["low"]).replace(0, np.nan)
        group["orderbook_imbalance"] = ((group["close"] - group["open"]) / price_range).fillna(
            0.0
        ).clip(-1.0, 1.0)
        rolling_mean = group["close"].rolling(30, min_periods=5).mean()
        rolling_std = group["close"].rolling(30, min_periods=5).std().replace(0, np.nan)
        group["overextension_z"] = ((group["close"] - rolling_mean) / rolling_std).fillna(0.0)
        group["rolling_high"] = group["high"].shift(1).rolling(30, min_periods=1).max()
        group["rolling_low"] = group["low"].shift(1).rolling(30, min_periods=1).min()
        group["time_of_day"] = group["timestamp"].dt.hour + group["timestamp"].dt.minute / 60.0
        group["day_of_week"] = group["timestamp"].dt.dayofweek
        expected_gap = pd.Timedelta(minutes=1) * 2
        gaps = group["timestamp"].diff().fillna(pd.Timedelta(minutes=1))
        group["stale_or_missing_data"] = gaps > expected_gap
        pieces.append(group)
    return pd.concat(pieces).sort_values(["symbol", "timestamp"]).reset_index(drop=True)
