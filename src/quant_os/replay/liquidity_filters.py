from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class LiquidityPolicy:
    min_liquidity_score: float = 0.20
    thin_liquidity_score: float = 0.40
    max_spread_bps: float = 12.0
    min_top_of_book_notional: float = 500.0
    thin_top_of_book_notional: float = 2_500.0
    max_quote_age_ms: float = 5_000.0
    thin_fill_ratio_multiplier: float = 0.50


@dataclass(frozen=True)
class LiquidityDecision:
    allowed: bool
    reason: str | None
    fill_ratio_multiplier: float = 1.0
    liquidity_label: str = "normal"
    spread_regime: str = "normal"


class LiquidityGate:
    def __init__(self, *, policy: LiquidityPolicy | None = None) -> None:
        self.policy = policy or LiquidityPolicy()

    def evaluate(self, row: pd.Series | dict[str, Any]) -> LiquidityDecision:
        policy = self.policy
        liquidity_score = _float(row, "liquidity_score", 1.0)
        spread_bps = _float(row, "spread_bps", 0.0)
        quote_age_ms = _float(row, "quote_age_ms", 0.0)
        top_of_book_notional = _float(row, "top_of_book_notional", float("inf"))

        if quote_age_ms > policy.max_quote_age_ms:
            return LiquidityDecision(False, "STALE_BOOK")
        if spread_bps > policy.max_spread_bps:
            return LiquidityDecision(False, "SPREAD_REGIME_TOO_WIDE", spread_regime="wide")
        if liquidity_score < policy.min_liquidity_score:
            return LiquidityDecision(False, "LIQUIDITY_TOO_WEAK")
        if top_of_book_notional < policy.min_top_of_book_notional:
            return LiquidityDecision(False, "LIQUIDITY_TOO_WEAK")

        thin = (
            liquidity_score < policy.thin_liquidity_score
            or top_of_book_notional < policy.thin_top_of_book_notional
        )
        if thin:
            return LiquidityDecision(
                True,
                "THIN_BOOK",
                fill_ratio_multiplier=policy.thin_fill_ratio_multiplier,
                liquidity_label="thin",
                spread_regime="thin",
            )
        return LiquidityDecision(True, None)


def _float(row: pd.Series | dict[str, Any], key: str, default: float) -> float:
    value = row.get(key, default)
    if pd.isna(value):
        return default
    return float(value)
