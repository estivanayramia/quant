from __future__ import annotations

from pathlib import Path

from quant_os.research.crypto.candidate_strategies import (
    generate_crypto_candidate_signals,
    strategy_failure_modes,
)
from quant_os.research.crypto.features import build_crypto_features
from quant_os.research.crypto.ingest import build_crypto_research_dataset
from quant_os.research.crypto.reports import write_crypto_research_report


def test_crypto_ingestion_builds_offline_btc_eth_dataset(tmp_path: Path) -> None:
    result = build_crypto_research_dataset(output_root=tmp_path, periods=72)

    assert result.dataset_id == "crypto_btc_eth_1m"
    assert result.frame["symbol"].unique().tolist() == ["BTC/USDT", "ETH/USDT"]
    assert result.frame["venue"].unique().tolist() == ["binance"]
    assert result.record.layer.value == "normalized"
    assert result.record.quality["status"] == "PASS"


def test_crypto_features_are_deterministic_and_market_specific(tmp_path: Path) -> None:
    dataset = build_crypto_research_dataset(output_root=tmp_path, periods=96)
    first = build_crypto_features(dataset.frame)
    second = build_crypto_features(dataset.frame)

    expected = {
        "volatility_regime",
        "spread_bps",
        "liquidity_score",
        "orderbook_imbalance",
        "overextension_z",
        "time_of_day",
        "day_of_week",
        "stale_or_missing_data",
    }
    assert expected.issubset(first.columns)
    expected_columns = sorted(expected)
    assert first[expected_columns].reset_index(drop=True).equals(
        second[expected_columns].reset_index(drop=True)
    )
    assert first["stale_or_missing_data"].sum() == 0


def test_crypto_candidate_strategies_include_controls_and_reason_codes(tmp_path: Path) -> None:
    dataset = build_crypto_research_dataset(output_root=tmp_path, periods=144)
    features = build_crypto_features(dataset.frame)
    first = generate_crypto_candidate_signals(features, seed=17)
    second = generate_crypto_candidate_signals(features, seed=17)

    strategy_ids = {signal.strategy_id for signal in first}
    assert "low_frequency_breakout" in strategy_ids
    assert "short_horizon_mean_reversion" in strategy_ids
    assert "overextension_fade" in strategy_ids
    assert "random_placebo" in strategy_ids
    assert "no_trade" not in strategy_ids
    assert [signal.model_dump() for signal in first] == [signal.model_dump() for signal in second]
    assert all(signal.reason_code for signal in first)
    assert "fails in high spread regimes" in strategy_failure_modes()["short_horizon_mean_reversion"]


def test_crypto_research_report_compares_placebo_and_failure_modes(tmp_path: Path) -> None:
    dataset = build_crypto_research_dataset(output_root=tmp_path, periods=144)
    payload = write_crypto_research_report(dataset.frame, output_root=tmp_path)

    assert payload["live_trading_enabled"] is False
    assert payload["symbols"] == ["BTC/USDT", "ETH/USDT"]
    assert "random_placebo" in payload["baseline_comparisons"]
    assert "no_trade" in payload["baseline_comparisons"]
    assert payload["failure_modes"]["overextension_fade"]
    assert (tmp_path / "reports" / "crypto" / "latest_research.json").exists()
    assert (tmp_path / "reports" / "crypto" / "latest_research.md").exists()
