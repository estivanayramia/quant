from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd


def load_backtest_runs(db_path: str | Path = "data/read_models/quant_os.duckdb") -> pd.DataFrame:
    with duckdb.connect(str(db_path)) as con:
        return con.execute("select * from backtest_runs").fetch_df()
