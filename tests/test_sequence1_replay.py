from __future__ import annotations

import pandas as pd
import pytest

from quant_os.replay.engine import ReplayEngine, ReplayOrderIntent
from quant_os.replay.fills import FillAssumption, apply_partial_fill
from quant_os.replay.latency import LatencyModel


def _events() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01T00:00:00Z", periods=4, freq="min"),
            "symbol": ["BTC/USDT"] * 4,
            "open": [100.0, 101.0, 103.0, 102.0],
            "high": [101.0, 104.0, 104.0, 103.0],
            "low": [99.0, 100.0, 101.0, 100.0],
            "close": [101.0, 103.0, 102.0, 101.0],
            "volume": [50.0, 60.0, 55.0, 40.0],
            "spread_bps": [2.0, 2.5, 3.0, 2.0],
            "liquidity_score": [0.9, 0.8, 0.7, 0.6],
        }
    )


def test_replay_fees_and_slippage_reduce_equity() -> None:
    events = _events()
    intents = [
        ReplayOrderIntent("s1", "BTC/USDT", "BUY", 1.0, events.loc[0, "timestamp"]),
        ReplayOrderIntent("s1", "BTC/USDT", "SELL", 1.0, events.loc[2, "timestamp"]),
    ]
    free = ReplayEngine(fee_bps=0.0, slippage_bps=0.0).run(events, intents)
    costly = ReplayEngine(fee_bps=10.0, slippage_bps=10.0).run(events, intents)

    assert costly.metrics["final_equity"] < free.metrics["final_equity"]
    assert costly.metrics["expectancy_after_costs"] < free.metrics["expectancy_after_costs"]


def test_partial_fill_logic_and_portfolio_accounting_reconcile() -> None:
    fill = apply_partial_fill(
        ReplayOrderIntent("s1", "BTC/USDT", "BUY", 2.0, pd.Timestamp("2026-01-01T00:00:00Z")),
        price=100.0,
        assumption=FillAssumption(fill_ratio=0.4, fee_bps=5.0, slippage_bps=2.0),
    )
    assert fill.quantity == pytest.approx(0.8)
    assert fill.remaining_quantity == pytest.approx(1.2)

    result = ReplayEngine(fill_ratio=0.5).run(
        _events(),
        [ReplayOrderIntent("s1", "BTC/USDT", "BUY", 2.0, _events().loc[0, "timestamp"])],
    )
    assert result.portfolio.positions["BTC/USDT"].quantity == pytest.approx(1.0)
    assert result.reconciliation["status"] == "PASS"


def test_passive_vs_aggressive_and_rejection_timeout_paths() -> None:
    events = _events()
    timestamp = events.loc[0, "timestamp"]
    passive = ReplayEngine(passive_fill_probability=1.0).run(
        events, [ReplayOrderIntent("s1", "BTC/USDT", "BUY", 1.0, timestamp, mode="passive")]
    )
    aggressive = ReplayEngine().run(
        events, [ReplayOrderIntent("s1", "BTC/USDT", "BUY", 1.0, timestamp, mode="aggressive")]
    )
    rejected = ReplayEngine(max_spread_bps=1.0).run(
        events, [ReplayOrderIntent("s1", "BTC/USDT", "BUY", 1.0, timestamp)]
    )
    timed_out = ReplayEngine(latency_model=LatencyModel(milliseconds=120_000)).run(
        events, [ReplayOrderIntent("s1", "BTC/USDT", "BUY", 1.0, timestamp, timeout_ms=1_000)]
    )

    assert passive.fills[0].price < aggressive.fills[0].price
    assert rejected.rejections[0]["reason"] == "SPREAD_TOO_WIDE"
    assert timed_out.rejections[0]["reason"] == "ORDER_TIMEOUT"


def test_replay_metrics_include_sequence1_risk_dimensions() -> None:
    events = _events()
    result = ReplayEngine().run(
        events,
        [
            ReplayOrderIntent("s1", "BTC/USDT", "BUY", 1.0, events.loc[0, "timestamp"]),
            ReplayOrderIntent("s1", "BTC/USDT", "SELL", 1.0, events.loc[2, "timestamp"]),
        ],
    )

    expected = {
        "expectancy_after_costs",
        "max_drawdown",
        "sharpe_after_costs",
        "trade_count",
        "turnover",
        "time_in_market",
        "capacity_approximation",
        "parameter_sensitivity",
    }
    assert expected.issubset(result.metrics)
