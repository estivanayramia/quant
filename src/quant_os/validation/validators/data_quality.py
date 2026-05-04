from __future__ import annotations

import pandas as pd


def data_is_fresh(latest_timestamp: pd.Timestamp, *, now: pd.Timestamp, max_age_minutes: int = 5) -> bool:
    return now - latest_timestamp <= pd.Timedelta(minutes=max_age_minutes)
