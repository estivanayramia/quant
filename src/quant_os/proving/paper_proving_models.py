from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CostModel:
    fee_bps: float
    slippage_bps: float
    spread_bps: float
    description: str

    def cost_for_notional(self, notional: float) -> float:
        return abs(notional) * (self.fee_bps + self.slippage_bps + self.spread_bps) / 10_000.0

    def to_report_dict(self) -> dict[str, Any]:
        return {
            "fee_bps": self.fee_bps,
            "slippage_bps": self.slippage_bps,
            "spread_bps": self.spread_bps,
            "description": self.description,
        }


@dataclass(frozen=True)
class FillModel:
    fill_probability: float
    average_fill_fraction: float
    description: str

    @property
    def effective_fill_fraction(self) -> float:
        return max(0.0, min(1.0, self.fill_probability * self.average_fill_fraction))

    def to_report_dict(self) -> dict[str, Any]:
        return {
            "fill_probability": self.fill_probability,
            "average_fill_fraction": self.average_fill_fraction,
            "effective_fill_fraction": self.effective_fill_fraction,
            "description": self.description,
        }


@dataclass(frozen=True)
class PaperSignalRow:
    timestamp: str
    signal: str
    strength: float
    provenance: str

    def to_report_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class PaperIntent:
    timestamp: str
    side: str
    entry_price: float
    exit_price: float
    quantity: float
    time_in_market_minutes: float

    def to_report_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class BaselineRow:
    name: str
    net_pnl: float
    description: str

    def to_report_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class PlaceboRow:
    name: str
    net_pnl: float
    description: str

    def to_report_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class PaperProvingInput:
    lane_id: str
    source_quality: str
    source_dependencies: tuple[str, ...]
    signals: tuple[PaperSignalRow, ...]
    intents: tuple[PaperIntent, ...]
    cost_model: CostModel | None
    fill_model: FillModel | None
    baselines: tuple[BaselineRow, ...]
    placebos: tuple[PlaceboRow, ...]
    min_trades_required: int
    oos_walk_forward_required: bool
    oos_walk_forward_status: str
    synthetic_only: bool
    trial_count: int
    trial_count_warning_present: bool
    live_fills_assumed_equal_to_paper: bool = False
    uses_copy_trade_or_wallet_mirroring: bool = False
    uses_leverage_futures_or_margin: bool = False

    def to_report_dict(self) -> dict[str, Any]:
        return {
            "lane_id": self.lane_id,
            "source_quality": self.source_quality,
            "source_dependencies": list(self.source_dependencies),
            "signals": [row.to_report_dict() for row in self.signals],
            "intents": [row.to_report_dict() for row in self.intents],
            "cost_model": None if self.cost_model is None else self.cost_model.to_report_dict(),
            "fill_model": None if self.fill_model is None else self.fill_model.to_report_dict(),
            "baselines": [row.to_report_dict() for row in self.baselines],
            "placebos": [row.to_report_dict() for row in self.placebos],
            "min_trades_required": self.min_trades_required,
            "oos_walk_forward_required": self.oos_walk_forward_required,
            "oos_walk_forward_status": self.oos_walk_forward_status,
            "synthetic_only": self.synthetic_only,
            "trial_count": self.trial_count,
            "trial_count_warning_present": self.trial_count_warning_present,
            "live_fills_assumed_equal_to_paper": self.live_fills_assumed_equal_to_paper,
            "uses_copy_trade_or_wallet_mirroring": self.uses_copy_trade_or_wallet_mirroring,
            "uses_leverage_futures_or_margin": self.uses_leverage_futures_or_margin,
        }
