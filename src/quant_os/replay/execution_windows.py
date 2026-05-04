from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pandas as pd


@dataclass(frozen=True)
class ExecutionWindow:
    allowed_hours_utc: set[int] | None = None
    allowed_weekdays_utc: set[int] | None = None

    def allows(self, timestamp: datetime | pd.Timestamp) -> bool:
        ts = pd.Timestamp(timestamp)
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        ts = ts.tz_convert("UTC")
        if self.allowed_hours_utc is not None and ts.hour not in self.allowed_hours_utc:
            return False
        if self.allowed_weekdays_utc is None:
            return True
        return ts.dayofweek in self.allowed_weekdays_utc
