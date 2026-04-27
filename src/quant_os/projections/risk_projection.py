from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd


def load_risk_decisions(db_path: str | Path = "data/read_models/quant_os.duckdb") -> pd.DataFrame:
    with duckdb.connect(str(db_path)) as con:
        return con.execute("select * from risk_decisions").fetch_df()
