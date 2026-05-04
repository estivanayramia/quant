from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd
from pydantic import BaseModel, ConfigDict

from quant_os.replay.adverse_selection import AdverseSelectionModel
from quant_os.replay.execution_windows import ExecutionWindow
from quant_os.replay.fills import FillAssumption, ReplayFill, apply_partial_fill
from quant_os.replay.latency import LatencyModel
from quant_os.replay.liquidity_filters import LiquidityDecision, LiquidityGate
from quant_os.replay.market_impact import MarketImpactModel
from quant_os.replay.metrics import replay_metrics
from quant_os.replay.portfolio import ReplayPortfolio
from quant_os.replay.session_rules import CryptoSessionRules


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
        liquidity_gate: LiquidityGate | None = None,
        market_impact_model: MarketImpactModel | None = None,
        adverse_selection_model: AdverseSelectionModel | None = None,
        execution_window: ExecutionWindow | None = None,
        session_rules: CryptoSessionRules | None = None,
        starting_cash: float = 10_000.0,
    ) -> None:
        self.fee_bps = fee_bps
        self.slippage_bps = slippage_bps
        self.fill_ratio = fill_ratio
        self.passive_fill_probability = passive_fill_probability
        self.max_spread_bps = max_spread_bps
        self.latency_model = latency_model or LatencyModel()
        self.liquidity_gate = liquidity_gate
        self.market_impact_model = market_impact_model
        self.adverse_selection_model = adverse_selection_model
        self.execution_window = execution_window
        self.session_rules = session_rules
        self.starting_cash = starting_cash

    def run(self, events: pd.DataFrame, intents: list[ReplayOrderIntent]) -> ReplayResult:
        market = events.sort_values(["symbol", "timestamp"]).copy()
        market["timestamp"] = pd.to_datetime(market["timestamp"], utc=True)
        portfolio = ReplayPortfolio(starting_cash=self.starting_cash, cash=self.starting_cash)
        fills: list[ReplayFill] = []
        rejections: list[dict[str, Any]] = []
        prices: dict[str, float] = {}
        equity_curve: list[float] = []
        realism_penalty_bps = 0.0
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
                decision = self._liquidity_decision(row)
                liquidity = self._liquidity_label(intent, decision)
                price, penalty_bps = self._realistic_price(float(row["close"]), row, intent)
                realism_penalty_bps += penalty_bps
                assumption = FillAssumption(
                    fill_ratio=self.fill_ratio * decision.fill_ratio_multiplier,
                    fee_bps=self.fee_bps,
                    slippage_bps=0.0 if liquidity == "passive" else self.slippage_bps,
                )
                fill = apply_partial_fill(
                    intent,
                    price=price,
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
        metrics["realism_penalty_bps"] = float(realism_penalty_bps)
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
        if self.execution_window is not None and not self.execution_window.allows(effective_timestamp):
            return {
                "strategy_id": intent.strategy_id,
                "symbol": intent.symbol,
                "reason": "EXECUTION_WINDOW_CLOSED",
            }
        if self.session_rules is not None:
            session_reason = self.session_rules.blocked_reason(effective_timestamp)
            if session_reason:
                return {
                    "strategy_id": intent.strategy_id,
                    "symbol": intent.symbol,
                    "reason": session_reason,
                }
        if float(row.get("spread_bps", 0.0)) > self.max_spread_bps:
            return {"strategy_id": intent.strategy_id, "symbol": intent.symbol, "reason": "SPREAD_TOO_WIDE"}
        if float(row.get("liquidity_score", 1.0)) <= 0.0:
            return {"strategy_id": intent.strategy_id, "symbol": intent.symbol, "reason": "NO_LIQUIDITY"}
        decision = self._liquidity_decision(row)
        if not decision.allowed:
            return {
                "strategy_id": intent.strategy_id,
                "symbol": intent.symbol,
                "reason": decision.reason or "LIQUIDITY_REJECTED",
            }
        return None

    def _liquidity_decision(self, row: pd.Series) -> LiquidityDecision:
        if self.liquidity_gate is None:
            return LiquidityDecision(True, None)
        return self.liquidity_gate.evaluate(row)

    def _liquidity_label(
        self,
        intent: ReplayOrderIntent,
        decision: LiquidityDecision,
    ) -> str:
        if decision.liquidity_label == "thin":
            return "thin"
        return "passive" if intent.mode == "passive" else "aggressive"

    def _realistic_price(
        self,
        price: float,
        row: pd.Series,
        intent: ReplayOrderIntent,
    ) -> tuple[float, float]:
        adjusted = float(price)
        penalty_bps = 0.0
        if self.market_impact_model is not None:
            result = self.market_impact_model.apply(
                price=adjusted,
                row=row,
                side=intent.side,
                quantity=intent.quantity,
                mode=intent.mode,
            )
            adjusted = result.price
            penalty_bps += result.impact_bps
        if self.adverse_selection_model is not None:
            result = self.adverse_selection_model.apply(
                price=adjusted,
                row=row,
                side=intent.side,
                mode=intent.mode,
            )
            adjusted = result.price
            penalty_bps += result.penalty_bps
        return adjusted, penalty_bps


def _reconcile(portfolio: ReplayPortfolio) -> dict[str, Any]:
    bad_positions = [
        symbol for symbol, position in portfolio.positions.items() if position.quantity < -1e-12
    ]
    return {"status": "PASS" if not bad_positions else "FAIL", "bad_positions": bad_positions}
