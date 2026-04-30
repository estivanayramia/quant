from __future__ import annotations

from pathlib import Path

import duckdb

from quant_os.canary.readiness import evaluate_canary_readiness


def rebuild_canary_projection(db_path: str | Path = "data/read_models/read_models.duckdb") -> Path:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = evaluate_canary_readiness(write=False)
    with duckdb.connect(str(path)) as conn:
        conn.execute(
            "CREATE OR REPLACE TABLE canary_readiness AS SELECT ? AS readiness_status, ? AS live_promotion_status, ? AS blockers_json",
            [payload["readiness_status"], payload["live_promotion_status"], str(payload["blockers"])],
        )
    return path
