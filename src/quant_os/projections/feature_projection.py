from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import pandas as pd


def rebuild_feature_projection(
    frame: pd.DataFrame,
    db_path: str | Path = "data/read_models/quant_os.duckdb",
) -> Path:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    try:
        con.execute("drop table if exists feature_summary")
        rows: list[dict[str, Any]] = []
        for symbol, group in frame.groupby("symbol"):
            rows.append(
                {
                    "symbol": symbol,
                    "rows": len(group),
                    "latest_timestamp": str(group["timestamp"].max()),
                    "columns": len(group.columns),
                }
            )
        con.register("feature_summary_df", pd.DataFrame(rows))
        con.execute("create table feature_summary as select * from feature_summary_df")
    finally:
        con.close()
    return path
