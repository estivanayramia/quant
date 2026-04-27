from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from quant_os.core.events import EventType, make_event
from quant_os.data.quality import validate_ohlcv
from quant_os.ports.event_store import EventStorePort

DEMO_SYMBOLS = ["BTC-USD", "ETH-USD", "SPY", "QQQ"]


def generate_demo_ohlcv(
    symbols: list[str] | None = None,
    periods: int = 180,
    seed: int = 42,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    symbols = symbols or DEMO_SYMBOLS
    dates = pd.date_range("2025-01-01", periods=periods, freq="D", tz="UTC")
    starts = {"BTC-USD": 42_000.0, "ETH-USD": 2_400.0, "SPY": 475.0, "QQQ": 410.0}
    frames: list[pd.DataFrame] = []
    for symbol in symbols:
        drift = 0.0005 if symbol in {"SPY", "QQQ"} else 0.0008
        shocks = rng.normal(drift, 0.018, size=periods)
        close = starts.get(symbol, 100.0) * np.exp(np.cumsum(shocks))
        open_ = close * (1 + rng.normal(0.0, 0.003, size=periods))
        spread = np.abs(rng.normal(0.007, 0.002, size=periods))
        high = np.maximum(open_, close) * (1 + spread)
        low = np.minimum(open_, close) * (1 - spread)
        volume = rng.uniform(100_000, 1_000_000, size=periods)
        frames.append(
            pd.DataFrame(
                {
                    "timestamp": dates,
                    "symbol": symbol,
                    "open": open_,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": volume,
                }
            )
        )
    return pd.concat(frames, ignore_index=True).sort_values(["symbol", "timestamp"])


def seed_demo_data(
    output_dir: str | Path = "data/demo",
    event_store: EventStorePort | None = None,
) -> dict[str, object]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    frame = generate_demo_ohlcv()
    summary = validate_ohlcv(frame)
    for symbol, group in frame.groupby("symbol"):
        group.to_parquet(output / f"{symbol}.parquet", index=False)
    if event_store is not None:
        event_store.append(
            make_event(
                EventType.DATA_SEEDED,
                "demo-data",
                {"summary": summary, "output_dir": str(output)},
            )
        )
    return summary
