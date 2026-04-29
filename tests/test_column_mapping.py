from __future__ import annotations

from quant_os.data.column_mapping import infer_column_mapping


def test_column_mapping_infers_common_aliases() -> None:
    mapping = infer_column_mapping(["date", "ticker", "o", "h", "l", "c", "vol"])
    assert mapping == {
        "timestamp": "date",
        "symbol": "ticker",
        "open": "o",
        "high": "h",
        "low": "l",
        "close": "c",
        "volume": "vol",
    }
