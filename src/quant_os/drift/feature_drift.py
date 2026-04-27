from __future__ import annotations

import pandas as pd

from quant_os.drift.data_drift import DriftSignal
from quant_os.features.technical import atr_like_range, returns, volatility


def detect_feature_drift(frame: pd.DataFrame, zscore_threshold: float = 3.0) -> DriftSignal:
    data = frame.sort_values("timestamp").copy()
    data["returns"] = data.groupby("symbol")["close"].transform(returns)
    data["volatility"] = data.groupby("symbol")["close"].transform(
        lambda series: volatility(series, 20)
    )
    data["atr_like"] = atr_like_range(data)
    midpoint = len(data) // 2
    reference = data.iloc[:midpoint]
    current = data.iloc[midpoint:]
    max_abs_z = 0.0
    for column in ["returns", "volatility", "atr_like"]:
        ref_mean = float(reference[column].mean())
        ref_std = float(reference[column].std() or 0.0)
        cur_mean = float(current[column].mean())
        zscore = abs(cur_mean - ref_mean) / ref_std if ref_std > 1e-12 else 0.0
        max_abs_z = max(max_abs_z, zscore)
    detected = max_abs_z > zscore_threshold
    return DriftSignal(
        name="feature_drift",
        detected=detected,
        severity="warning" if detected else "ok",
        details={"max_abs_zscore": max_abs_z, "threshold": zscore_threshold},
    )
