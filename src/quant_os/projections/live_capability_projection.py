from __future__ import annotations

from pathlib import Path

import duckdb

from quant_os.live_canary.capabilities import inspect_exchange_capabilities


def rebuild_live_capability_projection(
    db_path: str | Path = "data/read_models/read_models.duckdb",
) -> Path:
    payload = inspect_exchange_capabilities(write=True)
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(path)) as con:
        con.execute(
            "CREATE OR REPLACE TABLE live_canary_capabilities AS "
            "SELECT ? AS status, ? AS adapter_mode, ? AS dependency_status, "
            "? AS settings_status, ? AS real_order_possible",
            [
                payload["status"],
                payload["adapter_mode"],
                payload["dependency_status"],
                payload["settings_status"],
                payload["real_order_possible"],
            ],
        )
    return path

