from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from quant_os.data.loaders import load_yaml

CRYPTO_SYMBOLS = {"BTC-USD", "ETH-USD", "SOL-USD"}
BASE_PRICES = {
    "BTC-USD": 42_000.0,
    "ETH-USD": 2_400.0,
    "SOL-USD": 95.0,
    "SPY": 475.0,
    "QQQ": 410.0,
    "AAPL": 190.0,
    "MSFT": 375.0,
    "NVDA": 700.0,
}
TIMEFRAME_FREQ = {"5m": "5min", "15m": "15min", "1h": "1h", "1d": "1D"}
SCHEMA_VERSION = "expanded_demo_ohlcv_v1"


def load_dataset_config(path: str | Path = "configs/datasets.yaml") -> dict[str, Any]:
    if Path(path).exists():
        return load_yaml(path)
    return {
        "random_seed": 42,
        "expanded_demo": {
            "symbols": list(BASE_PRICES),
            "timeframes": list(TIMEFRAME_FREQ),
            "days": {"crypto_intraday": 90, "equity_intraday": 90, "daily": 365},
        },
    }


def seed_expanded_demo_data(
    output_dir: str | Path = "data/demo_expanded",
    config_path: str | Path = "configs/datasets.yaml",
) -> dict[str, Any]:
    config = load_dataset_config(config_path)
    demo = config.get("expanded_demo", {})
    symbols = list(demo.get("symbols") or BASE_PRICES)
    timeframes = list(demo.get("timeframes") or TIMEFRAME_FREQ)
    seed = int(config.get("random_seed", 42))
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    rows_by_key: dict[str, int] = {}
    total_rows = 0
    for symbol_index, symbol in enumerate(symbols):
        for timeframe_index, timeframe in enumerate(timeframes):
            frame = generate_expanded_ohlcv(
                symbol,
                timeframe,
                seed=seed + (symbol_index * 100) + timeframe_index,
                config=config,
            )
            path = output / f"timeframe={timeframe}" / f"symbol={symbol}" / "ohlcv.parquet"
            path.parent.mkdir(parents=True, exist_ok=True)
            frame.to_parquet(path, index=False)
            key = f"{timeframe}/{symbol}"
            rows_by_key[key] = len(frame)
            total_rows += len(frame)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset_root": str(output),
        "data_source": "synthetic_demo",
        "schema_version": SCHEMA_VERSION,
        "symbols": symbols,
        "timeframes": timeframes,
        "rows": total_rows,
        "rows_by_symbol_timeframe": rows_by_key,
        "caveat": "Synthetic offline demo data. Not real market data.",
    }


def generate_expanded_ohlcv(
    symbol: str,
    timeframe: str,
    *,
    seed: int = 42,
    config: dict[str, Any] | None = None,
) -> pd.DataFrame:
    config = config or load_dataset_config()
    rng = np.random.default_rng(seed)
    timestamps = _timestamps(symbol, timeframe, config)
    regimes = _regime_sequence(len(timestamps))
    returns = np.zeros(len(timestamps), dtype="float64")
    for index, regime in enumerate(regimes):
        drift, vol = _regime_params(regime, symbol)
        returns[index] = rng.normal(drift, vol)
    prices = BASE_PRICES.get(symbol, 100.0) * np.exp(np.cumsum(returns))
    if "1d" in timeframe or symbol not in CRYPTO_SYMBOLS:
        _apply_gap_events(prices, rng)
    open_ = prices * (1 + rng.normal(0.0, 0.0018, size=len(prices)))
    spread = np.abs(rng.normal(0.004, 0.0015, size=len(prices)))
    high = np.maximum(open_, prices) * (1 + spread)
    low = np.minimum(open_, prices) * (1 - spread)
    volume = rng.uniform(100_000, 1_000_000, size=len(prices))
    if len(volume) > 10:
        spike_indexes = rng.choice(
            np.arange(len(volume)), size=max(1, len(volume) // 80), replace=False
        )
        volume[spike_indexes] *= rng.uniform(2.0, 5.0, size=len(spike_indexes))
    frame = pd.DataFrame(
        {
            "timestamp": timestamps,
            "symbol": symbol,
            "timeframe": timeframe,
            "open": open_,
            "high": high,
            "low": low,
            "close": prices,
            "volume": volume,
            "regime": regimes,
            "data_source": "synthetic_demo",
        }
    )
    return frame.sort_values("timestamp").reset_index(drop=True)


def _timestamps(symbol: str, timeframe: str, config: dict[str, Any]) -> pd.DatetimeIndex:
    days = config.get("expanded_demo", {}).get("days", {})
    daily_days = int(days.get("daily", 365))
    intraday_days = int(
        days.get("crypto_intraday" if symbol in CRYPTO_SYMBOLS else "equity_intraday", 90)
    )
    start = pd.Timestamp("2024-01-01", tz="UTC")
    if timeframe == "1d":
        periods = daily_days
        freq = TIMEFRAME_FREQ[timeframe]
        index = pd.date_range(start, periods=periods, freq=freq, tz="UTC")
        return index if symbol in CRYPTO_SYMBOLS else index[index.dayofweek < 5]
    end = start + pd.Timedelta(days=intraday_days)
    raw = pd.date_range(start, end, freq=TIMEFRAME_FREQ[timeframe], tz="UTC", inclusive="left")
    if symbol in CRYPTO_SYMBOLS:
        return raw
    session = raw[(raw.dayofweek < 5) & (raw.hour >= 14) & (raw.hour < 21)]
    return session


def _regime_sequence(length: int) -> np.ndarray:
    labels = np.array(
        ["trending_up", "trending_down", "choppy", "high_volatility", "low_volatility"]
    )
    if length == 0:
        return np.array([], dtype=str)
    segment = max(1, length // len(labels))
    regimes = np.repeat(labels, segment)
    if len(regimes) < length:
        regimes = np.concatenate([regimes, np.repeat(labels[-1], length - len(regimes))])
    return regimes[:length]


def _regime_params(regime: str, symbol: str) -> tuple[float, float]:
    crypto_scale = 1.5 if symbol in CRYPTO_SYMBOLS else 1.0
    params = {
        "trending_up": (0.00018 * crypto_scale, 0.0035 * crypto_scale),
        "trending_down": (-0.00016 * crypto_scale, 0.0038 * crypto_scale),
        "choppy": (0.0, 0.0025 * crypto_scale),
        "high_volatility": (0.0, 0.0080 * crypto_scale),
        "low_volatility": (0.00003, 0.0012 * crypto_scale),
    }
    return params.get(regime, (0.0, 0.003))


def _apply_gap_events(prices: np.ndarray, rng: np.random.Generator) -> None:
    if len(prices) < 20:
        return
    for index in np.linspace(
        10, len(prices) - 2, num=min(5, max(1, len(prices) // 1000)), dtype=int
    ):
        prices[index:] *= 1 + rng.choice([-1, 1]) * rng.uniform(0.01, 0.035)
