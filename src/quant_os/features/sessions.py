from __future__ import annotations

import pandas as pd


def session_bucket(timestamp: pd.Timestamp) -> str:
    ts = pd.Timestamp(timestamp)
    ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
    hour = ts.hour
    if 0 <= hour < 7:
        return "asia"
    if 7 <= hour < 13:
        return "london"
    if 13 <= hour < 21:
        return "new_york"
    return "overnight"


def add_session_features(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.sort_values(["symbol", "timestamp"]).copy()
    timestamps = pd.to_datetime(data["timestamp"], utc=True)
    data["hour"] = timestamps.dt.hour
    data["day_of_week"] = timestamps.dt.dayofweek
    data["is_weekend"] = data["day_of_week"].isin([5, 6])
    data["session"] = timestamps.map(session_bucket)
    session_key = [data["symbol"], timestamps.dt.date, data["session"]]
    data["session_high_so_far"] = data.groupby(session_key, sort=False)["high"].cummax()
    data["session_low_so_far"] = data.groupby(session_key, sort=False)["low"].cummin()
    return data
