from __future__ import annotations

from pathlib import Path

import duckdb

from quant_os.live_canary.live_status import live_canary_status


def rebuild_live_canary_projection(
    db_path: str | Path = "data/read_models/read_models.duckdb",
) -> Path:
    payload = live_canary_status(write=True)
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(path)) as con:
        con.execute(
            "CREATE OR REPLACE TABLE live_canary_status AS "
            "SELECT ? AS status, ? AS adapter_available, ? AS open_position_count, "
            "? AS live_fire_enabled",
            [
                payload["status"],
                payload["adapter_available"],
                payload["open_position_count"],
                payload["live_fire_enabled"],
            ],
        )
    return path

