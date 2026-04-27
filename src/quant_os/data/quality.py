from __future__ import annotations

from datetime import timedelta
from typing import Any

import pandas as pd

from quant_os.core.errors import DataQualityError
from quant_os.data.schemas import REQUIRED_OHLCV_COLUMNS


def validate_ohlcv(
    frame: pd.DataFrame,
    *,
    now: pd.Timestamp | None = None,
    future_tolerance: timedelta = timedelta(minutes=5),
) -> dict[str, Any]:
    missing = [column for column in REQUIRED_OHLCV_COLUMNS if column not in frame.columns]
    if missing:
        raise DataQualityError(f"missing required columns: {missing}")
    if frame[REQUIRED_OHLCV_COLUMNS].isnull().any().any():
        raise DataQualityError("required OHLCV values must not be null")

    data = frame.copy()
    data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True)

    duplicates = data.duplicated(["symbol", "timestamp"])
    if duplicates.any():
        raise DataQualityError("duplicate symbol/timestamp rows detected")

    for symbol, group in data.groupby("symbol"):
        if not group["timestamp"].is_monotonic_increasing:
            raise DataQualityError(f"timestamps are not sorted for {symbol}")

    if (data[["open", "high", "low", "close"]] <= 0).any().any():
        raise DataQualityError("prices must be positive")
    if (data["volume"] < 0).any():
        raise DataQualityError("volume must be non-negative")
    if (data["high"] < data[["open", "close"]].max(axis=1)).any():
        raise DataQualityError("OHLC invalid: high below open/close")
    if (data["low"] > data[["open", "close"]].min(axis=1)).any():
        raise DataQualityError("OHLC invalid: low above open/close")

    reference_now = now or pd.Timestamp.now(tz="UTC")
    if (data["timestamp"] > reference_now + future_tolerance).any():
        raise DataQualityError("timestamps exceed future tolerance")

    return {
        "rows": int(len(data)),
        "symbols": sorted(data["symbol"].unique().tolist()),
        "start": data["timestamp"].min().isoformat(),
        "end": data["timestamp"].max().isoformat(),
    }
