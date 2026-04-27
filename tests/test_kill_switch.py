from __future__ import annotations

from quant_os.core.commands import CandidateOrder
from quant_os.risk.firewall import RiskContext, RiskFirewall
from quant_os.risk.limits import RiskLimits


def test_kill_switch_blocks_orders():
    candidate = CandidateOrder(
        strategy_id="s1",
        symbol="SPY",
        side="BUY",
        quantity=1.0,
        current_price=10.0,
    )
    decision = RiskFirewall(RiskLimits()).check(candidate, RiskContext(kill_switch_active=True))
    assert not decision.approved
    assert "KILL_SWITCH_ACTIVE" in decision.reasons
