from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class LatencyModel:
    milliseconds: int = 0

    def apply(self, timestamp: pd.Timestamp) -> pd.Timestamp:
        return pd.Timestamp(timestamp) + pd.Timedelta(milliseconds=self.milliseconds)
