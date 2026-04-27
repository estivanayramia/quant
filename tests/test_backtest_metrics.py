from __future__ import annotations

from quant_os.research.backtest import run_backtest


def test_baseline_strategy_can_run(event_store, spy_frame):
    result = run_backtest(spy_frame, strategy="baseline_ma", event_store=event_store)
    assert "final_equity" in result.metrics
    assert result.metrics["final_equity"] > 0
