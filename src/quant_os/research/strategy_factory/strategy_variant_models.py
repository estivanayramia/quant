from __future__ import annotations

from typing import Any, TypedDict


class StrategyVariant(TypedDict):
    id: str
    batch_index: int
    universe_cycle: int
    family: str
    assets: list[str]
    source: str
    lookback: int
    holding_window: int
    thresholds: dict[str, float]
    spread_cap_bps: float
    liquidity_cap_usd: float
    fee_model: dict[str, float]
    fill_model: dict[str, Any]
    no_trade_conditions: list[str]
    risk_cap: dict[str, float]
    expected_failure_modes: list[str]
    pre_registration_timestamp: str
    deterministic_seed: int
    no_live_metadata: dict[str, Any]
