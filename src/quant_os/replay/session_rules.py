from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd


@dataclass(frozen=True)
class SessionBlock:
    start_hour_utc: int
    end_hour_utc: int
    reason: str = "SESSION_BLOCKED"


@dataclass(frozen=True)
class CryptoSessionRules:
    blocked_windows: list[SessionBlock] = field(default_factory=list)

    def blocked_reason(self, timestamp: datetime | pd.Timestamp) -> str | None:
        ts = pd.Timestamp(timestamp)
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        hour = ts.tz_convert("UTC").hour
        for window in self.blocked_windows:
            if window.start_hour_utc <= window.end_hour_utc:
                blocked = window.start_hour_utc <= hour < window.end_hour_utc
            else:
                blocked = hour >= window.start_hour_utc or hour < window.end_hour_utc
            if blocked:
                return window.reason
        return None
