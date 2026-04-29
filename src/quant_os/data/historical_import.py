from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from quant_os.data.data_license import DEFAULT_LICENSE_NOTE
from quant_os.data.historical_cache import (
    DEFAULT_FIXTURE,
    IMPORT_ROOT,
    RAW_DIR,
    assert_safe_import_path,
    ensure_historical_dirs,
    now_utc,
    sha256_file,
    write_json,
)
from quant_os.data.historical_normalize import (
    normalize_historical_frame,
    read_ohlcv_file,
    write_normalized_historical,
)


def import_historical_csv(
    input_path: str | Path = DEFAULT_FIXTURE,
    *,
    symbol: str | None = None,
    timeframe: str = "1d",
    source_name: str = "fixture_local",
    license_note: str = DEFAULT_LICENSE_NOTE,
    column_mapping: dict[str, str] | None = None,
    allow_external_path: bool = False,
) -> dict[str, Any]:
    ensure_historical_dirs()
    source = assert_safe_import_path(input_path, allow_external_path=allow_external_path)
    if source.suffix.lower() not in {".csv", ".parquet"}:
        msg = f"unsupported historical import type: {source.suffix}"
        raise ValueError(msg)
    raw_hash = sha256_file(source)
    raw_copy = RAW_DIR / f"{source.stem}_{raw_hash[:12]}{source.suffix.lower()}"
    if source.resolve() != raw_copy.resolve():
        shutil.copy2(source, raw_copy)
    raw_frame = read_ohlcv_file(raw_copy)
    normalized, metadata = normalize_historical_frame(
        raw_frame,
        symbol=symbol,
        timeframe=timeframe,
        source_name=source_name,
        column_mapping=column_mapping,
    )
    normalized_summary = write_normalized_historical(
        normalized, source_name=source_name, timeframe=timeframe
    )
    payload = {
        "status": "IMPORTED",
        "imported_at": now_utc(),
        "source_type": "user_provided_file",
        "source_name": source_name,
        "license_note": license_note,
        "input_path": str(source),
        "raw_path": str(raw_copy),
        "raw_sha256": sha256_file(raw_copy),
        "normalized_path": normalized_summary["normalized_path"],
        "normalized_sha256": normalized_summary["normalized_sha256"],
        "rows": normalized_summary["rows"],
        "symbol": symbol,
        "timeframe": timeframe,
        "column_mapping": metadata["column_mapping"],
        "missing_columns": metadata["missing_columns"],
        "live_trading_enabled": False,
    }
    write_json(IMPORT_ROOT / "latest_import.json", payload)
    return payload
