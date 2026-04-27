from __future__ import annotations

from quant_os.research.backtest import run_backtest


def test_placebo_strategy_can_run(event_store, spy_frame):
    result = run_backtest(spy_frame, strategy="placebo_random", event_store=event_store)
    assert "total_return" in result.metrics
