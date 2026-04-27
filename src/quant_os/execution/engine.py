from __future__ import annotations

from pydantic import BaseModel

from quant_os.adapters.broker_simulated import SimulatedBroker
from quant_os.core.commands import CandidateOrder
from quant_os.core.events import EventType, make_event
from quant_os.domain.fills import Fill
from quant_os.domain.orders import Order, OrderStatus
from quant_os.domain.portfolio import PortfolioState
from quant_os.domain.risk import RiskDecision
from quant_os.execution.oms import OMS
from quant_os.execution.pms import PMS
from quant_os.ports.event_store import EventStorePort
from quant_os.risk.firewall import RiskContext, RiskFirewall


class ExecutionResult(BaseModel):
    order: Order
    decision: RiskDecision
    fill: Fill | None = None


class ExecutionEngine:
    def __init__(
        self,
        event_store: EventStorePort,
        risk_firewall: RiskFirewall,
        portfolio: PortfolioState | None = None,
        broker: SimulatedBroker | None = None,
    ) -> None:
        self.event_store = event_store
        self.risk_firewall = risk_firewall
        self.portfolio = portfolio or PortfolioState()
        self.oms = OMS(event_store)
        self.pms = PMS(event_store, self.portfolio)
        self.broker = broker or SimulatedBroker()
        self.trades_today = 0
        self.current_trade_date = None
        self.kill_switch_active = False
        self.quarantined_strategies: set[str] = set()

    def process_candidate(
        self,
        candidate: CandidateOrder,
        *,
        slippage_bps: float = 1.0,
        fee_bps: float = 1.0,
        execute: bool = True,
    ) -> ExecutionResult:
        order = self.oms.create_order(candidate)
        trade_date = candidate.created_at.date()
        if self.current_trade_date != trade_date:
            self.current_trade_date = trade_date
            self.trades_today = 0
        position = self.portfolio.positions.get(candidate.symbol)
        context = RiskContext(
            kill_switch_active=self.kill_switch_active,
            quarantined_strategies=self.quarantined_strategies,
            open_positions=self.portfolio.open_position_count,
            existing_symbol_quantity=position.quantity if position else 0.0,
            existing_symbol_notional=self.portfolio.position_notional(
                candidate.symbol, candidate.current_price
            ),
            trades_today=self.trades_today,
        )
        decision = self.risk_firewall.check(candidate, context, order.client_order_id)
        if not decision.approved:
            self.oms.reject(order, decision.reasons)
            return ExecutionResult(order=order, decision=decision)
        self.oms.submit(order)
        self.oms.accept(order)
        if not execute:
            return ExecutionResult(order=order, decision=decision)
        fill = self.broker.simulate_fill(order, candidate.current_price, slippage_bps, fee_bps)
        order.transition_to(OrderStatus.FILLED)
        self.event_store.append(
            make_event(
                EventType.ORDER_FILLED,
                order.client_order_id,
                {"order": order.model_dump(mode="json"), "fill": fill.model_dump(mode="json")},
            )
        )
        self.pms.apply_fill(fill)
        self.trades_today += 1
        return ExecutionResult(order=order, decision=decision, fill=fill)

    def activate_kill_switch(self, reason: str) -> None:
        self.kill_switch_active = True
        self.event_store.append(
            make_event(EventType.KILL_SWITCH_ACTIVATED, "global-kill-switch", {"reason": reason})
        )

    def deactivate_kill_switch(self) -> None:
        self.kill_switch_active = False
        self.event_store.append(
            make_event(EventType.KILL_SWITCH_DEACTIVATED, "global-kill-switch", {})
        )

    def quarantine_strategy(self, strategy_id: str, reason: str) -> None:
        self.quarantined_strategies.add(strategy_id)
        self.event_store.append(
            make_event(
                EventType.STRATEGY_QUARANTINED,
                strategy_id,
                {"strategy_id": strategy_id, "reason": reason},
            )
        )
