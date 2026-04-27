from __future__ import annotations

from quant_os.core.commands import CandidateOrder
from quant_os.risk.firewall import RiskContext, RiskFirewall
from quant_os.risk.limits import RiskLimits


def test_quarantined_strategy_is_blocked():
    candidate = CandidateOrder(
        strategy_id="bad_strategy",
        symbol="SPY",
        side="BUY",
        quantity=1.0,
        current_price=10.0,
    )
    decision = RiskFirewall(RiskLimits()).check(
        candidate,
        RiskContext(quarantined_strategies={"bad_strategy"}),
    )
    assert not decision.approved
    assert "STRATEGY_QUARANTINED" in decision.reasons
