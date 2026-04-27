from __future__ import annotations

import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from quant_os.core.errors import DataQualityError
from quant_os.data.quality import validate_ohlcv


def test_data_quality_catches_bad_ohlc(spy_frame):
    bad = spy_frame.copy()
    bad.loc[0, "high"] = bad.loc[0, "low"] * 0.5
    with pytest.raises(DataQualityError):
        validate_ohlcv(bad)


def test_data_quality_catches_duplicate_timestamps(spy_frame):
    bad = pd.concat([spy_frame, spy_frame.iloc[[0]]], ignore_index=True)
    with pytest.raises(DataQualityError):
        validate_ohlcv(bad)


@given(
    price=st.floats(min_value=1.0, max_value=1000.0),
    spread=st.floats(min_value=0.0, max_value=20.0),
)
def test_ohlc_validity_property(price: float, spread: float):
    frame = pd.DataFrame(
        {
            "timestamp": [pd.Timestamp("2025-01-01", tz="UTC")],
            "symbol": ["TST"],
            "open": [price],
            "high": [price + spread],
            "low": [max(0.01, price - spread)],
            "close": [price],
            "volume": [1.0],
        }
    )
    summary = validate_ohlcv(frame)
    assert summary["rows"] == 1
