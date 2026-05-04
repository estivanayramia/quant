from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd
from pydantic import BaseModel, ConfigDict

from quant_os.replay.fills import FillAssumption, ReplayFill, apply_partial_fill
from quant_os.replay.latency import LatencyModel
from quant_os.replay.metrics import replay_metrics
from quant_os.replay.portfolio import ReplayPortfolio


@dataclass(frozen=True)
class ReplayOrderIntent:
    strategy_id: str
    symbol: str
    side: str
    quantity: float
    timestamp: datetime
    mode: str = "aggressive"
    timeout_ms: int = 30_000
    reason_code: str = "RESEARCH_SIGNAL"


class ReplayResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    fills: list[ReplayFill]
    rejections: list[dict[str, Any]]
    portfolio: ReplayPortfolio
    equity_curve: list[float]
    metrics: dict[str, Any]
    reconciliation: dict[str, Any]
    live_trading_enabled: bool = False


class ReplayEngine:
    def __init__(
        self,
        *,
        fee_bps: float = 1.0,
        slippage_bps: float = 1.0,
        fill_ratio: float = 1.0,
        passive_fill_probability: float = 0.75,
        max_spread_bps: float = 10.0,
        latency_model: LatencyModel | None = None,
        starting_cash: float = 10_000.0,
    ) -> None:
        self.fee_bps = fee_bps
        self.slippage_bps = slippage_bps
        self.fill_ratio = fill_ratio
        self.passive_fill_probability = passive_fill_probability
        self.max_spread_bps = max_spread_bps
        self.latency_model = latency_model or LatencyModel()
        self.starting_cash = starting_cash

    def run(self, events: pd.DataFrame, intents: list[ReplayOrderIntent]) -> ReplayResult:
        market = events.sort_values(["symbol", "timestamp"]).copy()
        market["timestamp"] = pd.to_datetime(market["timestamp"], utc=True)
        portfolio = ReplayPortfolio(starting_cash=self.starting_cash, cash=self.starting_cash)
        fills: list[ReplayFill] = []
        rejections: list[dict[str, Any]] = []
        prices: dict[str, float] = {}
        equity_curve: list[float] = []
        intent_queue = sorted(intents, key=lambda item: pd.Timestamp(item.timestamp))
        for _, row in market.iterrows():
            timestamp = pd.Timestamp(row["timestamp"])
            symbol = str(row["symbol"])
            prices[symbol] = float(row["close"])
            due = [
                intent
                for intent in intent_queue
                if intent.symbol == symbol and self.latency_model.apply(pd.Timestamp(intent.timestamp)) <= timestamp
            ]
            for intent in due:
                intent_queue.remove(intent)
                rejection = self._rejection_reason(intent, row)
                if rejection:
                    rejections.append(rejection)
                    continue
                liquidity = "passive" if intent.mode == "passive" else "aggressive"
                assumption = FillAssumption(
                    fill_ratio=self.fill_ratio,
                    fee_bps=self.fee_bps,
                    slippage_bps=0.0 if liquidity == "passive" else self.slippage_bps,
                )
                fill = apply_partial_fill(
                    intent,
                    price=float(row["close"]),
                    assumption=assumption,
                    liquidity=liquidity,
                    timestamp=timestamp,
                )
                if fill.quantity > 0:
                    portfolio.apply_fill(fill)
                    fills.append(fill)
            equity_curve.append(portfolio.mark_to_market(prices))
        for intent in intent_queue:
            rejections.append({"strategy_id": intent.strategy_id, "symbol": intent.symbol, "reason": "NO_MARKET_EVENT"})
        metrics = replay_metrics(
            fills,
            equity_curve,
            starting_cash=self.starting_cash,
            turnover=portfolio.turnover,
            bars=len(market),
        )
        return ReplayResult(
            fills=fills,
            rejections=rejections,
            portfolio=portfolio,
            equity_curve=equity_curve,
            metrics=metrics,
            reconciliation=_reconcile(portfolio),
        )

    def _rejection_reason(self, intent: ReplayOrderIntent, row: pd.Series) -> dict[str, Any] | None:
        effective_timestamp = self.latency_model.apply(pd.Timestamp(intent.timestamp))
        if effective_timestamp - pd.Timestamp(intent.timestamp) > pd.Timedelta(milliseconds=intent.timeout_ms):
            return {"strategy_id": intent.strategy_id, "symbol": intent.symbol, "reason": "ORDER_TIMEOUT"}
        if float(row.get("spread_bps", 0.0)) > self.max_spread_bps:
            return {"strategy_id": intent.strategy_id, "symbol": intent.symbol, "reason": "SPREAD_TOO_WIDE"}
        if float(row.get("liquidity_score", 1.0)) <= 0.0:
            return {"strategy_id": intent.strategy_id, "symbol": intent.symbol, "reason": "NO_LIQUIDITY"}
        return None


def _reconcile(portfolio: ReplayPortfolio) -> dict[str, Any]:
    bad_positions = [
        symbol for symbol, position in portfolio.positions.items() if position.quantity < -1e-12
    ]
    return {"status": "PASS" if not bad_positions else "FAIL", "bad_positions": bad_positions}
