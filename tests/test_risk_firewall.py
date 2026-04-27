from __future__ import annotations

from quant_os.core.commands import CandidateOrder
from quant_os.risk.firewall import RiskContext, RiskFirewall
from quant_os.risk.limits import RiskLimits


def _candidate(**kwargs):
    data = {
        "strategy_id": "s1",
        "symbol": "SPY",
        "side": "BUY",
        "quantity": 1.0,
        "current_price": 10.0,
    }
    data.update(kwargs)
    return CandidateOrder(**data)


def test_risk_firewall_rejects_when_live_trading_disabled(event_store):
    firewall = RiskFirewall(RiskLimits(), event_store)
    decision = firewall.check(_candidate(live_requested=True), RiskContext())
    assert not decision.approved
    assert "LIVE_TRADING_DISABLED" in decision.reasons


def test_risk_firewall_rejects_when_max_order_notional_exceeded():
    decision = RiskFirewall(RiskLimits(max_order_notional=5.0)).check(_candidate())
    assert not decision.approved
    assert "MAX_ORDER_NOTIONAL" in decision.reasons


def test_risk_firewall_rejects_when_max_open_positions_exceeded():
    decision = RiskFirewall(RiskLimits(max_open_positions=1)).check(
        _candidate(),
        RiskContext(open_positions=1),
    )
    assert not decision.approved
    assert "MAX_OPEN_POSITIONS" in decision.reasons
