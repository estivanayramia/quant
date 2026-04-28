from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import pandas as pd


def rebuild_strategy_results_projection(
    results: dict[str, Any],
    db_path: str | Path = "data/read_models/quant_os.duckdb",
) -> Path:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for strategy_id, result in results.items():
        metrics = result.get("metrics", {})
        rows.append(
            {
                "strategy_id": strategy_id,
                "total_return": metrics.get("total_return", 0.0),
                "max_drawdown": metrics.get("max_drawdown", 0.0),
                "number_of_trades": metrics.get("number_of_trades", 0),
                "status": result.get("status", "RESEARCH_ONLY"),
            }
        )
    con = duckdb.connect(str(path))
    try:
        con.execute("drop table if exists strategy_results")
        con.register("strategy_results_df", pd.DataFrame(rows))
        con.execute("create table strategy_results as select * from strategy_results_df")
    finally:
        con.close()
    return path
