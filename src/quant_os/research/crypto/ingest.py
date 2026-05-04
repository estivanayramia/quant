from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict

from quant_os.data.normalization import normalize_dataset_frame
from quant_os.data.schemas import DatasetKind, DatasetLayer
from quant_os.data.stores import DatasetRecord, LocalDatasetStore


class CryptoDatasetResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    dataset_id: str
    frame: pd.DataFrame
    record: DatasetRecord
    source: str
    live_trading_enabled: bool = False


def build_crypto_research_dataset(
    *,
    output_root: str | Path = ".",
    periods: int = 240,
    source: str = "fixture_binance",
) -> CryptoDatasetResult:
    raw = generate_crypto_fixture(periods=periods)
    normalized = normalize_dataset_frame(raw, DatasetKind.CANDLE)
    store = LocalDatasetStore(Path(output_root) / "data" / "sequence1")
    record = store.write_dataset(
        normalized,
        dataset_id="crypto_btc_eth_1m",
        kind=DatasetKind.CANDLE,
        layer=DatasetLayer.NORMALIZED,
        source=source,
    )
    return CryptoDatasetResult(
        dataset_id="crypto_btc_eth_1m",
        frame=normalized,
        record=record,
        source=source,
    )


def generate_crypto_fixture(
    *,
    symbols: tuple[str, ...] = ("BTC/USDT", "ETH/USDT"),
    periods: int = 240,
    start: str = "2026-01-01T00:00:00Z",
) -> pd.DataFrame:
    rng = np.random.default_rng(151)
    timestamps = pd.date_range(start, periods=periods, freq="min")
    bases = {"BTC/USDT": 50_000.0, "ETH/USDT": 3_000.0}
    rows: list[dict[str, Any]] = []
    for symbol in symbols:
        base = bases.get(symbol, 1_000.0)
        for index, timestamp in enumerate(timestamps):
            seasonal = math.sin(index / 9.0) * 0.0018 + math.cos(index / 23.0) * 0.0012
            impulse = 0.004 if index in {48, 120, 180} else -0.003 if index in {80, 160} else 0.0
            drift = index * 0.00002
            noise = rng.normal(0.0, 0.00055)
            close = base * (1.0 + drift + seasonal + impulse + noise)
            open_price = base * (1.0 + drift + seasonal * 0.7)
            high = max(open_price, close) * (1.0 + 0.0015 + abs(noise))
            low = min(open_price, close) * (1.0 - 0.0013 - abs(noise) / 2)
            volume = (100 + index % 40) * (2.0 if symbol.startswith("BTC") else 5.0)
            spread_bps = 2.0 + (index % 7) * 0.2 + (0.8 if impulse else 0.0)
            rows.append(
                {
                    "timestamp": timestamp,
                    "symbol": symbol,
                    "venue": "binance",
                    "timeframe": "1m",
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": volume,
                    "spread_bps": spread_bps,
                    "source": "offline_fixture",
                }
            )
    return pd.DataFrame(rows)


def fetch_binance_public_klines(
    symbol: str,
    *,
    interval: str = "1m",
    limit: int = 500,
    timeout_seconds: int = 10,
) -> pd.DataFrame:
    query = urlencode({"symbol": symbol.replace("/", ""), "interval": interval, "limit": limit})
    url = f"https://api.binance.com/api/v3/klines?{query}"
    with urlopen(url, timeout=timeout_seconds) as response:  # nosec B310 - explicit public market data.
        payload = json.loads(response.read().decode("utf-8"))
    rows = [
        {
            "timestamp": pd.to_datetime(item[0], unit="ms", utc=True),
            "symbol": symbol,
            "venue": "binance",
            "timeframe": interval,
            "open": float(item[1]),
            "high": float(item[2]),
            "low": float(item[3]),
            "close": float(item[4]),
            "volume": float(item[5]),
            "source": "binance_public",
        }
        for item in payload
    ]
    return normalize_dataset_frame(pd.DataFrame(rows), DatasetKind.CANDLE)
