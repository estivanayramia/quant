from __future__ import annotations

import pandas as pd

from quant_os.research.backtest import BacktestResult, run_backtest


def run_placebo(frame: pd.DataFrame) -> BacktestResult:
    return run_backtest(frame, strategy="placebo_random")
