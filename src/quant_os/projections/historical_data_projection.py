from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from quant_os.data.historical_cache import NORMALIZED_LATEST


def rebuild_historical_data_projection(
    db_path: str | Path = "data/read_models/quant_os.duckdb",
) -> Path:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS historical_ohlcv (
                timestamp TIMESTAMP,
                symbol VARCHAR,
                timeframe VARCHAR,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume DOUBLE,
                source VARCHAR
            )
            """
        )
        conn.execute("DELETE FROM historical_ohlcv")
        if NORMALIZED_LATEST.exists():
            frame = pd.read_parquet(NORMALIZED_LATEST)
            conn.register("historical_frame", frame)
            conn.execute(
                """
                INSERT INTO historical_ohlcv
                SELECT
                    timestamp,
                    symbol,
                    timeframe,
                    open,
                    high,
                    low,
                    close,
                    volume,
                    source
                FROM historical_frame
                """
            )
            conn.unregister("historical_frame")
    return path
