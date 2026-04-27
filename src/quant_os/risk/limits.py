from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from quant_os.data.loaders import load_yaml


class RiskLimits(BaseModel):
    max_open_positions: int = 1
    max_trades_per_day: int = 3
    max_daily_loss_pct: float = 2.0
    max_weekly_loss_pct: float = 5.0
    max_position_notional: float = 100.0
    max_order_notional: float = 25.0
    max_spread_bps: float = 10.0
    max_slippage_bps: float = 15.0
    cooldown_after_loss_minutes: int = 60
    kill_switch_enabled: bool = False
    allow_leverage: bool = False
    allow_shorting: bool = False
    allow_options: bool = False
    allow_futures: bool = False
    allow_live_trading: bool = False

    @classmethod
    def from_yaml(cls, path: str | Path = "configs/risk_limits.yaml") -> RiskLimits:
        return cls.model_validate(load_yaml(path))
