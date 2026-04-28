from __future__ import annotations

from quant_os.execution.engine import ExecutionEngine
from quant_os.research.candidate_strategies import (
    available_strategy_specs,
    candidate_orders_for_strategy,
)
from quant_os.risk.firewall import RiskFirewall
from quant_os.risk.limits import RiskLimits


def test_candidate_strategies_generate_signals(spy_frame) -> None:
    strategies = [spec.strategy_id for spec in available_strategy_specs()]
    counts = {
        strategy: len(candidate_orders_for_strategy(spy_frame, strategy, seed=42))
        for strategy in strategies
    }
    assert counts["no_trade"] == 0
    assert any(counts[strategy] > 0 for strategy in strategies if strategy != "no_trade")


def test_candidate_strategies_route_through_risk_firewall(spy_frame, event_store) -> None:
    candidates = candidate_orders_for_strategy(spy_frame, "baseline_momentum")
    assert candidates
    engine = ExecutionEngine(event_store, RiskFirewall(RiskLimits(), event_store))
    result = engine.process_candidate(candidates[0], execute=False)
    assert result.decision.approved in {True, False}
    assert result.order.strategy_id == "baseline_momentum"


def test_candidate_strategies_do_not_import_external_broker_sdks() -> None:
    import quant_os.research.candidate_strategies as module

    source_names = set(module.__dict__)
    assert "alpaca" not in source_names
    assert "ccxt" not in source_names
    assert "freqtrade" not in source_names
