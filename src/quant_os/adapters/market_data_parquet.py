from __future__ import annotations

from pathlib import Path

import pandas as pd


class LocalParquetMarketData:
    def __init__(self, root: str | Path = "data/demo") -> None:
        self.root = Path(root)

    def load(self, symbol: str | None = None) -> pd.DataFrame:
        if symbol is not None:
            path = self.root / f"{symbol}.parquet"
            return pd.read_parquet(path)
        frames = [pd.read_parquet(path) for path in sorted(self.root.glob("*.parquet"))]
        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, ignore_index=True).sort_values(["symbol", "timestamp"])

    def write(self, frame: pd.DataFrame, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(path, index=False)
