from __future__ import annotations

import pandas as pd
import pytest

from quant_os.replay.adverse_selection import AdverseSelectionModel
from quant_os.replay.engine import ReplayEngine, ReplayOrderIntent
from quant_os.replay.execution_windows import ExecutionWindow
from quant_os.replay.liquidity_filters import LiquidityGate, LiquidityPolicy
from quant_os.replay.market_impact import MarketImpactModel


def _events() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01T00:00:00Z", periods=4, freq="min"),
            "symbol": ["BTC/USDT"] * 4,
            "open": [100.0, 101.0, 102.0, 101.0],
            "high": [102.0, 103.0, 103.0, 102.0],
            "low": [99.0, 100.0, 100.0, 99.0],
            "close": [101.0, 102.0, 101.0, 100.0],
            "volume": [100.0, 2.0, 100.0, 100.0],
            "spread_bps": [2.0, 9.0, 2.0, 2.0],
            "liquidity_score": [0.9, 0.18, 0.9, 0.9],
            "top_of_book_notional": [50_000.0, 120.0, 50_000.0, 50_000.0],
            "quote_age_ms": [100.0, 100.0, 8_000.0, 100.0],
            "orderbook_imbalance": [0.1, 0.2, 0.85, 0.0],
            "volatility_regime": ["normal", "normal", "high", "normal"],
        }
    )


def test_illiquid_conditions_reduce_or_reject_fills() -> None:
    events = _events()
    policy = LiquidityPolicy(
        min_liquidity_score=0.15,
        thin_liquidity_score=0.30,
        min_top_of_book_notional=100.0,
        thin_top_of_book_notional=1_000.0,
    )
    result = ReplayEngine(liquidity_gate=LiquidityGate(policy=policy)).run(
        events,
        [
            ReplayOrderIntent(
                "s2",
                "BTC/USDT",
                "BUY",
                1.0,
                events.loc[1, "timestamp"],
                reason_code="THIN_BOOK_TEST",
            ),
            ReplayOrderIntent(
                "s2",
                "BTC/USDT",
                "BUY",
                1.0,
                events.loc[1, "timestamp"],
                reason_code="REJECT_TEST",
            ),
        ],
    )

    assert result.fills[0].quantity == pytest.approx(0.5)
    assert result.fills[0].liquidity == "thin"

    stricter = ReplayEngine(
        liquidity_gate=LiquidityGate(
            policy=LiquidityPolicy(min_liquidity_score=0.25, min_top_of_book_notional=500.0)
        )
    ).run(
        events,
        [ReplayOrderIntent("s2", "BTC/USDT", "BUY", 1.0, events.loc[1, "timestamp"])],
    )
    assert stricter.rejections[0]["reason"] == "LIQUIDITY_TOO_WEAK"


def test_adverse_selection_and_market_impact_make_aggressive_path_worse() -> None:
    events = _events()
    intents = [
        ReplayOrderIntent("s2", "BTC/USDT", "BUY", 1.0, events.loc[0, "timestamp"]),
        ReplayOrderIntent("s2", "BTC/USDT", "SELL", 1.0, events.loc[3, "timestamp"]),
    ]
    baseline = ReplayEngine(fee_bps=0.0, slippage_bps=0.0).run(events, intents)
    realistic = ReplayEngine(
        fee_bps=0.0,
        slippage_bps=0.0,
        market_impact_model=MarketImpactModel(impact_bps_per_capacity=50.0),
        adverse_selection_model=AdverseSelectionModel(
            high_volatility_penalty_bps=4.0,
            imbalance_penalty_bps=3.0,
        ),
    ).run(events, intents)

    assert realistic.fills[0].price > baseline.fills[0].price
    assert realistic.metrics["final_equity"] < baseline.metrics["final_equity"]
    assert realistic.metrics["realism_penalty_bps"] > 0.0


def test_stale_book_and_execution_window_do_not_silently_pass() -> None:
    events = _events()
    stale = ReplayEngine(
        liquidity_gate=LiquidityGate(policy=LiquidityPolicy(max_quote_age_ms=5_000.0))
    ).run(
        events,
        [ReplayOrderIntent("s2", "BTC/USDT", "BUY", 1.0, events.loc[2, "timestamp"])],
    )
    windowed = ReplayEngine(execution_window=ExecutionWindow(allowed_hours_utc={1})).run(
        events,
        [ReplayOrderIntent("s2", "BTC/USDT", "BUY", 1.0, events.loc[0, "timestamp"])],
    )

    assert stale.rejections[0]["reason"] == "STALE_BOOK"
    assert windowed.rejections[0]["reason"] == "EXECUTION_WINDOW_CLOSED"


def test_realism_rejections_are_deterministic() -> None:
    events = _events()
    engine = ReplayEngine(
        liquidity_gate=LiquidityGate(
            policy=LiquidityPolicy(min_liquidity_score=0.25, max_quote_age_ms=5_000.0)
        )
    )
    intents = [
        ReplayOrderIntent("s2", "BTC/USDT", "BUY", 1.0, events.loc[1, "timestamp"]),
        ReplayOrderIntent("s2", "BTC/USDT", "BUY", 1.0, events.loc[2, "timestamp"]),
    ]

    first = engine.run(events, intents)
    second = engine.run(events, intents)

    assert [item["reason"] for item in first.rejections] == [
        item["reason"] for item in second.rejections
    ]
    assert [item["reason"] for item in first.rejections] == [
        "LIQUIDITY_TOO_WEAK",
        "STALE_BOOK",
    ]
