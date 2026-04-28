from __future__ import annotations

import pandas as pd

from quant_os.features.market_structure import (
    add_market_structure_features,
    detect_bos_choch,
    detect_fvg,
)


def _frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows).assign(
        timestamp=lambda data: pd.to_datetime(data["timestamp"], utc=True)
    )


def test_fvg_detects_simple_bullish_and_bearish_gap_cases() -> None:
    frame = _frame(
        [
            {
                "timestamp": "2025-01-01",
                "symbol": "SPY",
                "open": 10,
                "high": 11,
                "low": 9,
                "close": 10,
                "volume": 1,
            },
            {
                "timestamp": "2025-01-02",
                "symbol": "SPY",
                "open": 10,
                "high": 10.5,
                "low": 9.5,
                "close": 10,
                "volume": 1,
            },
            {
                "timestamp": "2025-01-03",
                "symbol": "SPY",
                "open": 12,
                "high": 13,
                "low": 12,
                "close": 12.5,
                "volume": 1,
            },
            {
                "timestamp": "2025-01-04",
                "symbol": "SPY",
                "open": 12,
                "high": 12.2,
                "low": 11.5,
                "close": 11.8,
                "volume": 1,
            },
            {
                "timestamp": "2025-01-05",
                "symbol": "SPY",
                "open": 8,
                "high": 8.5,
                "low": 7.5,
                "close": 8,
                "volume": 1,
            },
        ]
    )
    events = detect_fvg(frame)
    directions = {event["direction"] for event in events}
    assert {"bullish", "bearish"}.issubset(directions)


def test_bos_choch_interface_returns_deterministic_structure() -> None:
    frame = _frame(
        [
            {
                "timestamp": f"2025-01-{day:02d}",
                "symbol": "SPY",
                "open": 10 + day,
                "high": 11 + day,
                "low": 9 + day,
                "close": 10 + day,
                "volume": 1,
            }
            for day in range(1, 8)
        ]
    )
    first = detect_bos_choch(frame)
    second = detect_bos_choch(frame)
    assert first == second
    assert all("confidence" in event for event in first)


def test_market_structure_features_have_no_future_leakage_for_rolling_high(spy_frame) -> None:
    base = add_market_structure_features(spy_frame)
    changed = spy_frame.copy()
    changed.loc[changed.index[-1], "high"] = changed["high"].max() * 100
    rerun = add_market_structure_features(changed)
    pd.testing.assert_series_equal(
        base["rolling_high"].iloc[:50].reset_index(drop=True),
        rerun["rolling_high"].iloc[:50].reset_index(drop=True),
        check_names=False,
    )
