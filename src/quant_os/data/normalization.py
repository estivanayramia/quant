from __future__ import annotations

import re
from typing import Any

import pandas as pd

from quant_os.data.schemas import CANONICAL_SCHEMAS, DatasetKind

_QUOTE_ASSETS = ("USDT", "USDC", "USD", "BTC", "ETH")


def normalize_symbol(symbol: object) -> str:
    raw = str(symbol).strip().upper().replace("-", "/").replace("_", "/")
    if "/" in raw:
        base, quote = raw.split("/", 1)
        return f"{base}/{quote}"
    compact = re.sub(r"[^A-Z0-9]", "", raw)
    for quote in _QUOTE_ASSETS:
        if compact.endswith(quote) and len(compact) > len(quote):
            return f"{compact[:-len(quote)]}/{quote}"
    return compact


def normalize_timestamp(value: Any) -> pd.Timestamp:
    return pd.Timestamp(pd.to_datetime(value, utc=True))


def normalize_dataset_frame(frame: pd.DataFrame, kind: DatasetKind | str) -> pd.DataFrame:
    dataset_kind = DatasetKind(kind)
    schema = CANONICAL_SCHEMAS[dataset_kind]
    data = frame.copy()
    if "timestamp" in data.columns:
        data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True)
    if "symbol" in data.columns:
        data["symbol"] = data["symbol"].map(normalize_symbol)
    if dataset_kind == DatasetKind.CANDLE:
        data["venue"] = data.get("venue", "unknown")
        data["timeframe"] = data.get("timeframe", "unknown")
    data["dataset_kind"] = dataset_kind.value
    data["dataset_version"] = schema.version
    sort_columns = [column for column in ["symbol", "timestamp"] if column in data.columns]
    if sort_columns:
        data = data.sort_values(sort_columns)
    return data.reset_index(drop=True)
