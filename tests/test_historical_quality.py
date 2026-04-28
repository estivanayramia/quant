from __future__ import annotations

from pathlib import Path

import pandas as pd

from quant_os.data.historical_import import import_historical_csv
from quant_os.data.historical_quality import run_historical_quality, validate_historical_frame

FIXTURES = Path(__file__).parent / "fixtures" / "historical"


def test_invalid_ohlc_fails_quality(local_project) -> None:
    import_historical_csv(FIXTURES / "sample_ohlcv_bad_ohlc.csv")
    quality = run_historical_quality()
    assert quality["status"] == "FAIL"
    assert "INVALID_OHLC" in quality["failures"]


def test_duplicate_timestamps_fail_quality(local_project) -> None:
    import_historical_csv(FIXTURES / "sample_ohlcv_duplicates.csv")
    quality = run_historical_quality()
    assert quality["status"] == "FAIL"
    assert "DUPLICATE_SYMBOL_TIMEFRAME_TIMESTAMP" in quality["failures"]


def test_negative_price_fails_quality() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2024-01-01"], utc=True),
            "symbol": ["SPY"],
            "timeframe": ["1d"],
            "open": [-1],
            "high": [1],
            "low": [-2],
            "close": [0.5],
            "volume": [10],
        }
    )
    result = validate_historical_frame(frame)
    assert "NEGATIVE_PRICE" in result["failures"]
