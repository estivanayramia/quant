from __future__ import annotations

import pandas as pd


def add_liquidity_features(frame: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    data = frame.sort_values(["symbol", "timestamp"]).copy()
    pieces = []
    for _, group in data.groupby("symbol", sort=False):
        group = group.copy()
        prior_high = group["high"].shift(1).rolling(window=window, min_periods=1).max()
        prior_low = group["low"].shift(1).rolling(window=window, min_periods=1).min()
        rolling_high = group["high"].rolling(window=window, min_periods=1).max()
        rolling_low = group["low"].rolling(window=window, min_periods=1).min()
        group["prior_swing_high"] = prior_high
        group["prior_swing_low"] = prior_low
        group["rolling_high"] = rolling_high
        group["rolling_low"] = rolling_low
        group["distance_to_rolling_high"] = (rolling_high - group["close"]) / group["close"]
        group["distance_to_rolling_low"] = (group["close"] - rolling_low) / group["close"]
        group["breakout_above_rolling_high"] = group["close"] > prior_high
        group["breakdown_below_rolling_low"] = group["close"] < prior_low
        group["liquidity_sweep_up"] = (group["high"] > prior_high) & (group["close"] < prior_high)
        group["liquidity_sweep_down"] = (group["low"] < prior_low) & (group["close"] > prior_low)
        pieces.append(group)
    return pd.concat(pieces).sort_index()


def detect_liquidity_sweeps(frame: pd.DataFrame, window: int = 20) -> list[dict[str, object]]:
    data = add_liquidity_features(frame, window)
    events = []
    for _, row in data.iterrows():
        if bool(row.get("liquidity_sweep_up", False)):
            events.append(
                {"timestamp": row["timestamp"], "symbol": row["symbol"], "direction": "up"}
            )
        if bool(row.get("liquidity_sweep_down", False)):
            events.append(
                {"timestamp": row["timestamp"], "symbol": row["symbol"], "direction": "down"}
            )
    return events
