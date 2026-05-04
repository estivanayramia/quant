from __future__ import annotations

from datetime import timedelta
from typing import Any

import pandas as pd

from quant_os.core.errors import DataQualityError
from quant_os.data.schemas import CANONICAL_SCHEMAS, REQUIRED_OHLCV_COLUMNS, DatasetKind


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


def validate_canonical_frame(frame: pd.DataFrame, kind: DatasetKind | str) -> dict[str, Any]:
    dataset_kind = DatasetKind(kind)
    schema = CANONICAL_SCHEMAS[dataset_kind]
    missing = [column for column in schema.required_columns if column not in frame.columns]
    if missing:
        raise DataQualityError(f"MISSING_COLUMNS:{','.join(missing)}")
    data = frame.copy()
    if data[schema.required_columns].isnull().any().any():
        raise DataQualityError("NULL_REQUIRED_VALUES")
    if schema.timestamp_column in data.columns:
        data[schema.timestamp_column] = pd.to_datetime(data[schema.timestamp_column], utc=True)
    if data.duplicated(schema.primary_key).any():
        raise DataQualityError("DUPLICATE_PRIMARY_KEY")
    if dataset_kind == DatasetKind.CANDLE:
        _validate_candles(data)
    if dataset_kind in {DatasetKind.TRADE, DatasetKind.FILL} and (
        data[["price", "quantity"]] <= 0
    ).any().any():
        raise DataQualityError("NON_POSITIVE_PRICE_OR_QUANTITY")
    if dataset_kind == DatasetKind.ORDERBOOK_SNAPSHOT:
        if (data[["bid_price", "ask_price", "bid_size", "ask_size"]] <= 0).any().any():
            raise DataQualityError("NON_POSITIVE_ORDERBOOK_VALUE")
        if (data["bid_price"] >= data["ask_price"]).any():
            raise DataQualityError("CROSSED_ORDERBOOK")
    symbols = sorted(data["symbol"].dropna().astype(str).unique().tolist()) if "symbol" in data else []
    return {
        "status": "PASS",
        "rows": int(len(data)),
        "dataset_kind": dataset_kind.value,
        "dataset_version": schema.version,
        "symbols": symbols,
        "start": data[schema.timestamp_column].min().isoformat()
        if schema.timestamp_column in data
        else None,
        "end": data[schema.timestamp_column].max().isoformat()
        if schema.timestamp_column in data
        else None,
    }


def _validate_candles(data: pd.DataFrame) -> None:
    price_columns = ["open", "high", "low", "close"]
    if (data[price_columns] <= 0).any().any():
        raise DataQualityError("NON_POSITIVE_PRICE")
    if (data["volume"] < 0).any():
        raise DataQualityError("NEGATIVE_VOLUME")
    if (data["high"] < data[["open", "close"]].max(axis=1)).any():
        raise DataQualityError("INVALID_OHLC_HIGH")
    if (data["low"] > data[["open", "close"]].min(axis=1)).any():
        raise DataQualityError("INVALID_OHLC_LOW")
    for key, group in data.groupby(["venue", "symbol", "timeframe"], sort=False):
        if not group["timestamp"].is_monotonic_increasing:
            raise DataQualityError(f"NON_MONOTONIC_TIME:{key}")
