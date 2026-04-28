from __future__ import annotations

import pandas as pd

from quant_os.features.liquidity import add_liquidity_features, detect_liquidity_sweeps


def test_liquidity_sweep_detects_simple_sweep_cases() -> None:
    frame = pd.DataFrame(
        [
            {
                "timestamp": "2025-01-01",
                "symbol": "SPY",
                "open": 10,
                "high": 10,
                "low": 9,
                "close": 9.5,
                "volume": 1,
            },
            {
                "timestamp": "2025-01-02",
                "symbol": "SPY",
                "open": 9.5,
                "high": 10.5,
                "low": 9.3,
                "close": 9.8,
                "volume": 1,
            },
            {
                "timestamp": "2025-01-03",
                "symbol": "SPY",
                "open": 9.8,
                "high": 10,
                "low": 8.5,
                "close": 9.2,
                "volume": 1,
            },
        ]
    ).assign(timestamp=lambda data: pd.to_datetime(data["timestamp"], utc=True))
    events = detect_liquidity_sweeps(frame, window=2)
    directions = {event["direction"] for event in events}
    assert {"up", "down"}.issubset(directions)


def test_liquidity_rolling_features_do_not_use_future_rows(spy_frame) -> None:
    base = add_liquidity_features(spy_frame)
    changed = spy_frame.copy()
    changed.loc[changed.index[-1], "low"] = changed["low"].min() / 100
    rerun = add_liquidity_features(changed)
    assert base["prior_swing_low"].iloc[10] == rerun["prior_swing_low"].iloc[10]
