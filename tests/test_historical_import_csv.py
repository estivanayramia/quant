from __future__ import annotations

from pathlib import Path

import pandas as pd

from quant_os.data.historical_import import import_historical_csv
from quant_os.data.historical_quality import run_historical_quality

FIXTURES = Path(__file__).parent / "fixtures" / "historical"


def test_csv_import_works_with_standard_schema(local_project) -> None:
    payload = import_historical_csv(FIXTURES / "sample_ohlcv_standard.csv")
    assert payload["status"] == "IMPORTED"
    assert payload["rows"] == 10
    assert Path(payload["normalized_path"]).exists()


def test_csv_import_works_with_mapped_schema(local_project) -> None:
    payload = import_historical_csv(FIXTURES / "sample_ohlcv_mapped.csv")
    frame = pd.read_parquet(payload["normalized_path"])
    assert set(["timestamp", "symbol", "open", "high", "low", "close", "volume"]).issubset(
        frame.columns
    )
    assert frame["symbol"].iloc[0] == "AAPL"


def test_missing_columns_fail_quality(local_project) -> None:
    import_historical_csv(FIXTURES / "sample_ohlcv_missing_columns.csv")
    quality = run_historical_quality()
    assert quality["status"] == "FAIL"
    assert any("MISSING_COLUMNS" in item for item in quality["failures"])
