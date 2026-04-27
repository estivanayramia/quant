from __future__ import annotations

REQUIRED_OHLCV_COLUMNS = ["timestamp", "symbol", "open", "high", "low", "close", "volume"]


OHLCV_DTYPES = {
    "symbol": "string",
    "open": "float64",
    "high": "float64",
    "low": "float64",
    "close": "float64",
    "volume": "float64",
}
