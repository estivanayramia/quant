from __future__ import annotations

from pathlib import Path
from typing import Protocol

import pandas as pd


class MarketDataPort(Protocol):
    def load(self, symbol: str | None = None) -> pd.DataFrame: ...

    def write(self, frame: pd.DataFrame, path: Path) -> None: ...
