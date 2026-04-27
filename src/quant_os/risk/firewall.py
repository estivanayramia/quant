from __future__ import annotations

from pydantic import BaseModel, Field

from quant_os.core.commands import CandidateOrder
from quant_os.core.events import EventType, make_event
from quant_os.domain.risk import RiskDecision
from quant_os.ports.event_store import EventStorePort
from quant_os.risk.limits import RiskLimits
from quant_os.risk.no_trade import NoTradeEngine


class RiskContext(BaseModel):
    execution_mode: str = "simulated"
    kill_switch_active: bool = False
    quarantined_strategies: set[str] = Field(default_factory=set)
    open_positions: int = 0
    existing_symbol_quantity: float = 0.0
    existing_symbol_notional: float = 0.0
    trades_today: int = 0
    cooldown_active: bool = False
    leverage_requested: bool = False
    no_trade_reasons: list[str] = Field(default_factory=list)


class RiskFirewall:
    def __init__(
        self,
        limits: RiskLimits | None = None,
        event_store: EventStorePort | None = None,
        no_trade_engine: NoTradeEngine | None = None,
    ) -> None:
        self.limits = limits or RiskLimits()
        self.event_store = event_store
        self.no_trade_engine = no_trade_engine or NoTradeEngine()

    def check(
        self,
        candidate: CandidateOrder,
        context: RiskContext | None = None,
        client_order_id: str | None = None,
    ) -> RiskDecision:
        context = context or RiskContext()
        reasons: list[str] = []
        limits = self.limits

        if (
            candidate.live_requested or context.execution_mode == "live"
        ) and not limits.allow_live_trading:
            reasons.append("LIVE_TRADING_DISABLED")
        if context.kill_switch_active or limits.kill_switch_enabled:
            reasons.append("KILL_SWITCH_ACTIVE")
        if candidate.strategy_id in context.quarantined_strategies:
            reasons.append("STRATEGY_QUARANTINED")
        if (
            candidate.side.upper() == "BUY"
            and context.existing_symbol_quantity <= 0
            and context.open_positions >= limits.max_open_positions
        ):
            reasons.append("MAX_OPEN_POSITIONS")
        if context.trades_today >= limits.max_trades_per_day:
            reasons.append("MAX_TRADES_PER_DAY")
        if candidate.notional > limits.max_order_notional:
            reasons.append("MAX_ORDER_NOTIONAL")

        projected_notional = context.existing_symbol_notional
        if candidate.side.upper() == "BUY":
            projected_notional += candidate.notional
        else:
            projected_notional = max(0.0, projected_notional - candidate.notional)
            if (
                not limits.allow_shorting
                and candidate.quantity > context.existing_symbol_quantity + 1e-12
            ):
                reasons.append("SHORTING_DISABLED")
        if projected_notional > limits.max_position_notional:
            reasons.append("MAX_POSITION_NOTIONAL")

        if context.leverage_requested and not limits.allow_leverage:
            reasons.append("LEVERAGE_DISABLED")
        if "option" in candidate.asset_class.lower() and not limits.allow_options:
            reasons.append("OPTIONS_DISABLED")
        if "future" in candidate.asset_class.lower() and not limits.allow_futures:
            reasons.append("FUTURES_DISABLED")
        if candidate.estimated_spread_bps > limits.max_spread_bps:
            reasons.append("SPREAD_TOO_WIDE")
        if candidate.estimated_slippage_bps > limits.max_slippage_bps:
            reasons.append("SLIPPAGE_TOO_HIGH")
        if context.cooldown_active:
            reasons.append("COOLDOWN_AFTER_LOSS")

        no_trade = self.no_trade_engine.evaluate(candidate.no_trade, context.no_trade_reasons)
        if no_trade.blocked:
            reasons.extend(no_trade.reasons)

        decision = RiskDecision(
            approved=not reasons,
            reasons=reasons,
            limits_snapshot=limits.model_dump(),
            strategy_id=candidate.strategy_id,
            symbol=candidate.symbol,
            client_order_id=client_order_id,
        )
        self._append_decision(decision)
        return decision

    def _append_decision(self, decision: RiskDecision) -> None:
        if self.event_store is None:
            return
        event_type = EventType.RISK_APPROVED if decision.approved else EventType.RISK_REJECTED
        aggregate_id = decision.client_order_id or f"risk-{decision.strategy_id}-{decision.symbol}"
        self.event_store.append(
            make_event(
                event_type,
                aggregate_id,
                {"decision": decision.model_dump(mode="json")},
            )
        )
