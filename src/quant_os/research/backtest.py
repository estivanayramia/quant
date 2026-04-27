from __future__ import annotations

import pandas as pd
from pydantic import BaseModel

from quant_os.adapters.event_store_jsonl import JsonlEventStore
from quant_os.core.commands import CandidateOrder
from quant_os.core.events import EventType, make_event
from quant_os.domain.fills import Fill
from quant_os.execution.engine import ExecutionEngine
from quant_os.ports.event_store import EventStorePort
from quant_os.research.metrics import calculate_metrics
from quant_os.research.strategies import baseline_ma_candidates, placebo_random_candidates
from quant_os.risk.firewall import RiskFirewall
from quant_os.risk.limits import RiskLimits


class BacktestResult(BaseModel):
    strategy_id: str
    metrics: dict[str, float | int]
    fills: list[Fill]
    risk_rejections: int
    equity_curve: list[float]


def run_backtest(
    frame: pd.DataFrame,
    strategy: str = "baseline_ma",
    event_store: EventStorePort | None = None,
    limits: RiskLimits | None = None,
    slippage_bps: float = 2.0,
    fee_bps: float = 1.0,
    strategy_id: str | None = None,
    seed: int = 7,
) -> BacktestResult:
    event_store = event_store or JsonlEventStore()
    strategy_id = strategy_id or strategy
    event_store.append(
        make_event(
            EventType.BACKTEST_STARTED,
            strategy_id,
            {"strategy_id": strategy_id, "strategy": strategy, "slippage_bps": slippage_bps},
        )
    )
    symbol_frame = frame.sort_values("timestamp")
    candidates = _candidates_for_strategy(symbol_frame, strategy, strategy_id, seed)
    risk = RiskFirewall(limits or RiskLimits.from_yaml(), event_store)
    engine = ExecutionEngine(event_store, risk)
    fills: list[Fill] = []
    rejected = 0
    candidate_index = 0
    equity_values: list[float] = []
    candidate_by_time = {candidate.created_at: candidate for candidate in candidates}

    for _, row in symbol_frame.iterrows():
        timestamp = pd.Timestamp(row["timestamp"]).to_pydatetime()
        candidate = candidate_by_time.get(timestamp)
        if candidate is not None:
            result = engine.process_candidate(
                candidate,
                slippage_bps=slippage_bps,
                fee_bps=fee_bps,
                execute=True,
            )
            candidate_index += 1
            if result.fill is not None:
                fills.append(result.fill)
            if not result.decision.approved:
                rejected += 1
        price = float(row["close"])
        marked_positions = sum(
            position.quantity * price for position in engine.portfolio.positions.values()
        )
        equity_values.append(engine.portfolio.cash + marked_positions)

    equity_curve = pd.Series(equity_values, dtype="float64")
    metrics = calculate_metrics(fills, equity_curve, engine.portfolio.starting_cash)
    payload = {
        "strategy_id": strategy_id,
        "strategy": strategy,
        "metrics": metrics,
        "fills": len(fills),
        "risk_rejections": rejected,
        "candidates": candidate_index,
        "slippage_bps": slippage_bps,
        "fee_bps": fee_bps,
    }
    event_store.append(make_event(EventType.BACKTEST_COMPLETED, strategy_id, payload))
    return BacktestResult(
        strategy_id=strategy_id,
        metrics=metrics,
        fills=fills,
        risk_rejections=rejected,
        equity_curve=[float(value) for value in equity_values],
    )


def _candidates_for_strategy(
    frame: pd.DataFrame,
    strategy: str,
    strategy_id: str,
    seed: int,
) -> list[CandidateOrder]:
    if strategy == "baseline_ma":
        return baseline_ma_candidates(frame, strategy_id=strategy_id)
    if strategy == "placebo_random":
        return placebo_random_candidates(frame, strategy_id=strategy_id, seed=seed)
    msg = f"unknown strategy {strategy}"
    raise ValueError(msg)
