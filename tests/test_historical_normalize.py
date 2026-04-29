from __future__ import annotations

import pandas as pd

from quant_os.data.historical_normalize import normalize_historical_frame


def test_normalize_supports_common_column_aliases() -> None:
    frame = pd.DataFrame(
        {
            "date": ["2024-01-01"],
            "ticker": ["MSFT"],
            "o": [1],
            "h": [2],
            "l": [0.5],
            "c": [1.5],
            "vol": [100],
        }
    )
    normalized, metadata = normalize_historical_frame(frame, timeframe="1d")
    assert metadata["missing_columns"] == []
    assert normalized["timestamp"].dt.tz is not None
    assert normalized["symbol"].iloc[0] == "MSFT"
