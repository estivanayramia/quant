from __future__ import annotations

import pandas as pd

from quant_os.core.commands import CandidateOrder
from quant_os.execution.engine import ExecutionEngine
from quant_os.execution.reconciliation import rebuild_portfolio_from_events
from quant_os.risk.firewall import RiskFirewall
from quant_os.risk.limits import RiskLimits


def test_event_replay_rebuilds_state_deterministically(event_store):
    engine = ExecutionEngine(event_store, RiskFirewall(RiskLimits(), event_store))
    buy = CandidateOrder(
        strategy_id="s1",
        symbol="SPY",
        side="BUY",
        quantity=1.0,
        current_price=10.0,
        created_at=pd.Timestamp("2025-01-01", tz="UTC").to_pydatetime(),
    )
    sell = CandidateOrder(
        strategy_id="s1",
        symbol="SPY",
        side="SELL",
        quantity=1.0,
        current_price=11.0,
        created_at=pd.Timestamp("2025-01-02", tz="UTC").to_pydatetime(),
    )
    engine.process_candidate(buy)
    engine.process_candidate(sell)
    first = rebuild_portfolio_from_events(event_store.read_all())
    second = rebuild_portfolio_from_events(event_store.read_all())
    assert first.model_dump() == second.model_dump()
    assert first.open_position_count == 0
