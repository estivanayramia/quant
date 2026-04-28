from __future__ import annotations

import pandas as pd

from quant_os.data.dataset_quality import validate_dataset_frame


def _valid_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=3, freq="1h", tz="UTC"),
            "symbol": ["SPY"] * 3,
            "timeframe": ["1h"] * 3,
            "open": [10.0, 11.0, 12.0],
            "high": [11.0, 12.0, 13.0],
            "low": [9.0, 10.0, 11.0],
            "close": [10.5, 11.5, 12.5],
            "volume": [100.0, 110.0, 120.0],
        }
    )


def test_dataset_quality_catches_invalid_ohlc() -> None:
    frame = _valid_frame()
    frame.loc[0, "high"] = 8.0
    result = validate_dataset_frame(frame)
    assert result["status"] == "FAIL"
    assert "INVALID_OHLC" in result["failures"]


def test_dataset_quality_catches_duplicate_timestamps() -> None:
    frame = pd.concat([_valid_frame(), _valid_frame().iloc[[0]]], ignore_index=True)
    result = validate_dataset_frame(frame)
    assert result["status"] == "FAIL"
    assert "DUPLICATE_SYMBOL_TIMEFRAME_TIMESTAMP" in result["failures"]
