from __future__ import annotations

from pathlib import Path

import yaml

from quant_os.data.expanded_demo_data import generate_expanded_ohlcv, seed_expanded_demo_data


def _small_dataset_config() -> dict:
    return {
        "random_seed": 42,
        "expanded_demo": {
            "symbols": ["BTC-USD", "SPY"],
            "timeframes": ["1h", "1d"],
            "days": {"crypto_intraday": 3, "equity_intraday": 3, "daily": 8},
        },
    }


def test_expanded_demo_data_generation_is_deterministic() -> None:
    first = generate_expanded_ohlcv("BTC-USD", "1h", seed=123, config=_small_dataset_config())
    second = generate_expanded_ohlcv("BTC-USD", "1h", seed=123, config=_small_dataset_config())
    assert first["close"].round(8).tolist() == second["close"].round(8).tolist()


def test_expanded_demo_generates_multiple_symbols_and_timeframes(local_project) -> None:
    Path("configs/datasets.yaml").write_text(
        yaml.safe_dump(_small_dataset_config()), encoding="utf-8"
    )
    summary = seed_expanded_demo_data()
    assert set(summary["symbols"]) == {"BTC-USD", "SPY"}
    assert set(summary["timeframes"]) == {"1h", "1d"}
    assert Path("data/demo_expanded/timeframe=1h/symbol=BTC-USD/ohlcv.parquet").exists()
