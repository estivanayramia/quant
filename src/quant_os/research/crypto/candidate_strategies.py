from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from pydantic import BaseModel


class CryptoSignal(BaseModel):
    strategy_id: str
    symbol: str
    timestamp: datetime
    side: str
    strength: float
    expected_edge_bps: float
    confidence: float
    reason_code: str
    notes: str


def generate_crypto_candidate_signals(
    features: pd.DataFrame,
    *,
    seed: int = 42,
    min_edge_bps: float = 4.0,
) -> list[CryptoSignal]:
    data = features.sort_values(["symbol", "timestamp"]).copy()
    signals: list[CryptoSignal] = []
    for _, row in data.iterrows():
        if _breakout(row):
            edge = 8.0 + float(row["liquidity_score"]) * 5.0
            if edge >= min_edge_bps:
                signals.append(_signal(row, "low_frequency_breakout", "BUY", edge, "BREAKOUT_REGIME"))
        if _mean_reversion(row):
            edge = 6.0 + (1.0 - abs(float(row["orderbook_imbalance"]))) * 4.0
            if edge >= min_edge_bps:
                signals.append(
                    _signal(row, "short_horizon_mean_reversion", "BUY", edge, "LIQUID_REVERSAL")
                )
        if _overextension_fade(row):
            edge = 7.0 + min(abs(float(row["overextension_z"])), 4.0) * 2.0
            if edge >= min_edge_bps:
                signals.append(_signal(row, "overextension_fade", "SELL", edge, "OVEREXTENSION_FADE"))
    signals.extend(_random_placebo(data, seed=seed))
    return sorted(signals, key=lambda item: (item.symbol, item.timestamp, item.strategy_id))


def strategy_failure_modes() -> dict[str, list[str]]:
    return {
        "low_frequency_breakout": [
            "fails in fake-volume breakouts",
            "fails when volatility regime shifts before fills",
        ],
        "short_horizon_mean_reversion": [
            "fails in high spread regimes",
            "fails when orderbook imbalance reflects informed flow",
        ],
        "overextension_fade": [
            "fails in liquidation cascades",
            "fails when trend continuation overwhelms snapback behavior",
        ],
        "random_placebo": ["must underperform real candidates after costs"],
        "no_trade": ["capital preservation baseline; opportunity cost only"],
    }


def _breakout(row: pd.Series) -> bool:
    return (
        row["volatility_regime"] != "high"
        and float(row["close"]) > float(row["rolling_high"])
        and float(row["liquidity_score"]) >= 0.45
        and not bool(row["stale_or_missing_data"])
    )


def _mean_reversion(row: pd.Series) -> bool:
    return (
        float(row["returns"]) < -0.001
        and float(row["spread_bps"]) <= 4.0
        and float(row["liquidity_score"]) >= 0.35
        and abs(float(row["orderbook_imbalance"])) < 0.75
    )


def _overextension_fade(row: pd.Series) -> bool:
    return (
        float(row["overextension_z"]) > 1.8
        and float(row["spread_bps"]) <= 5.0
        and not bool(row["stale_or_missing_data"])
    )


def _signal(
    row: pd.Series,
    strategy_id: str,
    side: str,
    edge_bps: float,
    reason_code: str,
) -> CryptoSignal:
    confidence = max(0.05, min(0.95, 0.45 + float(row["liquidity_score"]) * 0.35))
    return CryptoSignal(
        strategy_id=strategy_id,
        symbol=str(row["symbol"]),
        timestamp=pd.Timestamp(row["timestamp"]).to_pydatetime(),
        side=side,
        strength=float(min(1.0, abs(float(row.get("overextension_z", 0.0))) / 4.0 + 0.25)),
        expected_edge_bps=float(edge_bps),
        confidence=float(confidence),
        reason_code=reason_code,
        notes="research signal only; deterministic execution gate remains outside AI authority",
    )


def _random_placebo(data: pd.DataFrame, *, seed: int) -> list[CryptoSignal]:
    rng = np.random.default_rng(seed)
    signals: list[CryptoSignal] = []
    for _, row in data.iterrows():
        if rng.random() < 0.015:
            signals.append(
                CryptoSignal(
                    strategy_id="random_placebo",
                    symbol=str(row["symbol"]),
                    timestamp=pd.Timestamp(row["timestamp"]).to_pydatetime(),
                    side="BUY",
                    strength=0.1,
                    expected_edge_bps=-2.0,
                    confidence=0.1,
                    reason_code="SEEDED_PLACEBO",
                    notes="negative-control seeded random signal",
                )
            )
    if not signals and not data.empty:
        row = data.iloc[len(data) // 2]
        signals.append(
            CryptoSignal(
                strategy_id="random_placebo",
                symbol=str(row["symbol"]),
                timestamp=pd.Timestamp(row["timestamp"]).to_pydatetime(),
                side="BUY",
                strength=0.1,
                expected_edge_bps=-2.0,
                confidence=0.1,
                reason_code="SEEDED_PLACEBO",
                notes="negative-control seeded random signal",
            )
        )
    return signals


def signals_to_rows(signals: list[CryptoSignal]) -> list[dict[str, Any]]:
    return [signal.model_dump(mode="json") for signal in signals]
