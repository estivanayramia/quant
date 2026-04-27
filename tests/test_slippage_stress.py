from __future__ import annotations

from quant_os.research.backtest import run_backtest


def test_slippage_stress_changes_results(event_store, spy_frame):
    normal = run_backtest(
        spy_frame,
        strategy="placebo_random",
        event_store=event_store,
        strategy_id="placebo_normal",
        slippage_bps=1.0,
    )
    stressed = run_backtest(
        spy_frame,
        strategy="placebo_random",
        event_store=event_store,
        strategy_id="placebo_stressed",
        slippage_bps=15.0,
    )
    assert normal.metrics["final_equity"] != stressed.metrics["final_equity"]
