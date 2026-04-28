from __future__ import annotations

from quant_os.research.candidate_strategies import STRATEGY_SPECS, StrategySpec


def list_research_strategies() -> list[StrategySpec]:
    return list(STRATEGY_SPECS.values())
