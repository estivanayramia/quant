from __future__ import annotations

import pandas as pd


def returns(close: pd.Series) -> pd.Series:
    return close.pct_change().fillna(0.0)


def moving_average(close: pd.Series, window: int) -> pd.Series:
    return close.rolling(window=window, min_periods=1).mean()


def volatility(close: pd.Series, window: int = 20) -> pd.Series:
    return returns(close).rolling(window=window, min_periods=2).std().fillna(0.0)


def atr_like_range(frame: pd.DataFrame, window: int = 14) -> pd.Series:
    ranges = (frame["high"] - frame["low"]) / frame["close"]
    return ranges.rolling(window=window, min_periods=1).mean()


def session_label(timestamp: pd.Timestamp) -> str:
    hour = pd.Timestamp(timestamp).tz_convert("UTC").hour
    if 13 <= hour < 20:
        return "us_session"
    if 7 <= hour < 13:
        return "europe_session"
    return "overnight"
