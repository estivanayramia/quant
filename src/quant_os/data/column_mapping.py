from __future__ import annotations

from typing import Any

import pandas as pd

CANONICAL_REQUIRED = ["timestamp", "symbol", "open", "high", "low", "close", "volume"]
ALIASES: dict[str, tuple[str, ...]] = {
    "timestamp": ("timestamp", "datetime", "date", "time"),
    "symbol": ("symbol", "ticker", "pair"),
    "open": ("open", "o"),
    "high": ("high", "h"),
    "low": ("low", "l"),
    "close": ("close", "c"),
    "volume": ("volume", "vol"),
}


def infer_column_mapping(
    columns: list[str] | pd.Index, explicit_mapping: dict[str, str] | None = None
) -> dict[str, str]:
    explicit_mapping = explicit_mapping or {}
    lowered = {str(column).lower(): str(column) for column in columns}
    mapping: dict[str, str] = {}
    for target in CANONICAL_REQUIRED:
        if target in explicit_mapping:
            mapping[target] = explicit_mapping[target]
            continue
        for alias in ALIASES[target]:
            if alias in lowered:
                mapping[target] = lowered[alias]
                break
    return mapping


def normalize_columns(
    frame: pd.DataFrame,
    *,
    symbol: str | None = None,
    timeframe: str = "1d",
    source_name: str = "user_provided_file",
    column_mapping: dict[str, str] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    mapping = infer_column_mapping(frame.columns, column_mapping)
    data = pd.DataFrame()
    missing: list[str] = []
    for target in CANONICAL_REQUIRED:
        source = mapping.get(target)
        if source and source in frame.columns:
            data[target] = frame[source]
        elif target == "symbol" and symbol:
            data[target] = symbol
        else:
            missing.append(target)
    if "timeframe" in frame.columns:
        data["timeframe"] = frame["timeframe"]
    else:
        data["timeframe"] = timeframe
    data["source"] = source_name
    for column in ["open", "high", "low", "close", "volume"]:
        if column in data.columns:
            data[column] = pd.to_numeric(data[column], errors="coerce")
    if "timestamp" in data.columns:
        data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True, errors="coerce")
    if set(CANONICAL_REQUIRED).issubset(data.columns):
        data = data.sort_values(["symbol", "timeframe", "timestamp"]).reset_index(drop=True)
    return data, {"column_mapping": mapping, "missing_columns": missing}
