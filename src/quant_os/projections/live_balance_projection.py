from __future__ import annotations

from pathlib import Path

import duckdb

from quant_os.live_canary.balance_snapshot import build_balance_snapshot
from quant_os.live_canary.exchange_factory import build_exchange_adapter


def rebuild_live_balance_projection(
    db_path: str | Path = "data/read_models/read_models.duckdb",
) -> Path:
    payload = build_balance_snapshot(build_exchange_adapter())
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(path)) as con:
        con.execute(
            "CREATE OR REPLACE TABLE live_canary_balance_snapshot AS "
            "SELECT ? AS adapter_available, ? AS exchange_name, ? AS positions_count",
            [
                payload["adapter_available"],
                payload["exchange_name"],
                len(payload["positions"]),
            ],
        )
    return path
