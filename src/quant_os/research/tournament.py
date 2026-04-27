from __future__ import annotations

from pathlib import Path

import pandas as pd

from quant_os.ports.event_store import EventStorePort
from quant_os.research.backtest import run_backtest
from quant_os.research.slippage import STRESS_LEVELS


def run_tournament(
    frame: pd.DataFrame,
    event_store: EventStorePort,
    output_path: str | Path = "reports/tournament_summary.json",
) -> dict[str, object]:
    results: dict[str, object] = {}
    for strategy in ["baseline_ma", "placebo_random"]:
        for level, params in STRESS_LEVELS.items():
            strategy_id = f"{strategy}_{level}"
            result = run_backtest(
                frame,
                strategy=strategy,
                event_store=event_store,
                strategy_id=strategy_id,
                slippage_bps=params["slippage_bps"],
                fee_bps=params["fee_bps"],
            )
            results[strategy_id] = result.metrics
    summary = {"results": results, "disclaimer": "This is simulation only. No live trading."}
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    import json

    path.write_text(json.dumps(summary, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return summary
