from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class AdverseSelectionResult:
    price: float
    penalty_bps: float


@dataclass(frozen=True)
class AdverseSelectionModel:
    high_volatility_penalty_bps: float = 3.0
    imbalance_penalty_bps: float = 2.0
    passive_penalty_multiplier: float = 0.50

    def apply(
        self,
        *,
        price: float,
        row: pd.Series | dict[str, Any],
        side: str,
        mode: str,
    ) -> AdverseSelectionResult:
        penalty = 0.0
        if str(row.get("volatility_regime", "")).lower() == "high":
            penalty += self.high_volatility_penalty_bps
        imbalance = _float(row, "orderbook_imbalance", 0.0)
        if _is_adverse_imbalance(side, imbalance):
            penalty += abs(imbalance) * self.imbalance_penalty_bps
        if mode == "passive":
            penalty *= self.passive_penalty_multiplier
        direction = 1.0 if side.upper() == "BUY" else -1.0
        adjusted = float(price) * (1.0 + direction * penalty / 10_000.0)
        return AdverseSelectionResult(price=adjusted, penalty_bps=float(penalty))


def _is_adverse_imbalance(side: str, imbalance: float) -> bool:
    return (side.upper() == "BUY" and imbalance > 0.0) or (
        side.upper() == "SELL" and imbalance < 0.0
    )


def _float(row: pd.Series | dict[str, Any], key: str, default: float) -> float:
    value = row.get(key, default)
    if pd.isna(value):
        return default
    return float(value)
