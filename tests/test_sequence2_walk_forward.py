from __future__ import annotations

import pandas as pd

from quant_os.research.validation.robustness import parameter_stability_warnings
from quant_os.research.validation.splits import rolling_walk_forward_splits
from quant_os.research.validation.walk_forward import run_crypto_walk_forward


def _crypto_frame(periods: int = 96) -> pd.DataFrame:
    timestamps = pd.date_range("2026-01-01T00:00:00Z", periods=periods, freq="min")
    rows = []
    for index, timestamp in enumerate(timestamps):
        trend = 0.25 if index < periods // 2 else -0.35
        close = 100.0 + index * trend + (index % 5) * 0.2
        rows.append(
            {
                "timestamp": timestamp,
                "symbol": "BTC/USDT",
                "open": close - 0.1,
                "high": close + 0.5,
                "low": close - 0.5,
                "close": close,
                "volume": 200.0 + (index % 7) * 10.0,
                "spread_bps": 2.0 if index % 11 else 4.0,
                "liquidity_score": 0.8,
            }
        )
    return pd.DataFrame(rows)


def test_rolling_splits_are_chronological() -> None:
    splits = rolling_walk_forward_splits(
        _crypto_frame(),
        train_bars=24,
        validation_bars=12,
        test_bars=12,
        step_bars=12,
    )

    assert len(splits) >= 3
    for split in splits:
        assert split.train["timestamp"].max() < split.validation["timestamp"].min()
        assert split.validation["timestamp"].max() < split.test["timestamp"].min()


def test_rolling_splits_do_not_split_shared_symbol_timestamps() -> None:
    btc = _crypto_frame(48)
    eth = btc.copy()
    eth["symbol"] = "ETH/USDT"
    splits = rolling_walk_forward_splits(
        pd.concat([btc, eth], ignore_index=True),
        train_bars=13,
        validation_bars=7,
        test_bars=7,
        step_bars=7,
    )

    assert splits
    for split in splits:
        assert set(split.train["timestamp"]).isdisjoint(set(split.validation["timestamp"]))
        assert set(split.validation["timestamp"]).isdisjoint(set(split.test["timestamp"]))


def test_unstable_parameters_are_flagged() -> None:
    warnings = parameter_stability_warnings(
        [
            {"selected_min_edge_bps": 4.0},
            {"selected_min_edge_bps": 10.0},
            {"selected_min_edge_bps": 4.0},
        ]
    )

    assert "UNSTABLE_PARAMETERS" in warnings


def test_walk_forward_reports_oos_metrics_and_regime_summary(tmp_path) -> None:
    payload = run_crypto_walk_forward(
        _crypto_frame(),
        train_bars=24,
        validation_bars=12,
        test_bars=12,
        step_bars=12,
        output_root=tmp_path,
    )

    assert payload["split_count"] >= 3
    assert payload["aggregate"]["mean_train_expectancy_after_costs_bps"] != payload["aggregate"][
        "mean_test_expectancy_after_costs_bps"
    ]
    assert payload["baselines"]["no_trade"]["expectancy_after_costs_bps"] == 0.0
    assert "random_placebo" in payload["baselines"]
    assert payload["regime_summary"]
    assert (tmp_path / "reports" / "sequence2" / "walk_forward" / "latest_walk_forward.json").exists()
    assert (tmp_path / "reports" / "sequence2" / "walk_forward" / "latest_walk_forward.md").exists()
