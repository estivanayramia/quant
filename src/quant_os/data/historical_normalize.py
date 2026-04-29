from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from quant_os.data.column_mapping import normalize_columns
from quant_os.data.historical_cache import (
    DEFAULT_FIXTURE,
    NORMALIZED_DIR,
    ensure_historical_dirs,
    latest_import_record,
    now_utc,
    sha256_file,
    write_json,
)

NORMALIZED_LATEST = NORMALIZED_DIR / "latest.parquet"


def read_ohlcv_file(path: str | Path) -> pd.DataFrame:
    source = Path(path)
    suffix = source.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(source)
    if suffix == ".parquet":
        return pd.read_parquet(source)
    msg = f"unsupported historical file type: {suffix}"
    raise ValueError(msg)


def normalize_historical_frame(
    frame: pd.DataFrame,
    *,
    symbol: str | None = None,
    timeframe: str = "1d",
    source_name: str = "user_provided_file",
    column_mapping: dict[str, str] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    data, metadata = normalize_columns(
        frame,
        symbol=symbol,
        timeframe=timeframe,
        source_name=source_name,
        column_mapping=column_mapping,
    )
    return data, metadata


def write_normalized_historical(
    frame: pd.DataFrame,
    *,
    source_name: str,
    timeframe: str,
    output_path: str | Path = NORMALIZED_LATEST,
) -> dict[str, Any]:
    ensure_historical_dirs()
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)
    symbol_values = sorted(frame["symbol"].dropna().astype(str).unique().tolist()) if "symbol" in frame else []
    payload = {
        "normalized_at": now_utc(),
        "normalized_path": str(path),
        "normalized_sha256": sha256_file(path),
        "rows": int(len(frame)),
        "symbols": symbol_values,
        "timeframes": sorted(frame["timeframe"].dropna().astype(str).unique().tolist())
        if "timeframe" in frame
        else [timeframe],
        "source_name": source_name,
    }
    write_json(NORMALIZED_DIR / "latest_normalized.json", payload)
    return payload


def normalize_latest_historical() -> dict[str, Any]:
    record = latest_import_record()
    raw_path = Path(record["raw_path"]) if record else DEFAULT_FIXTURE
    source_name = str(record.get("source_name", "fixture_local")) if record else "fixture_local"
    timeframe = str(record.get("timeframe", "1d")) if record else "1d"
    raw_symbol = record.get("symbol") if record else None
    symbol = str(raw_symbol) if raw_symbol else None
    frame = read_ohlcv_file(raw_path)
    normalized, metadata = normalize_historical_frame(
        frame, symbol=symbol, timeframe=timeframe, source_name=source_name
    )
    output = write_normalized_historical(normalized, source_name=source_name, timeframe=timeframe)
    output["normalization_metadata"] = metadata
    write_json(NORMALIZED_DIR / "latest_normalized.json", output)
    return output
