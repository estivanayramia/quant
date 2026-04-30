from __future__ import annotations

from pathlib import Path

import duckdb

from quant_os.canary.final_gate import evaluate_final_gate


def rebuild_canary_rehearsal_projection(
    db_path: str | Path = "data/read_models/read_models.duckdb",
) -> Path:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = evaluate_final_gate(write=False)
    with duckdb.connect(str(path)) as conn:
        conn.execute(
            "CREATE OR REPLACE TABLE canary_rehearsal AS SELECT ? AS final_gate_status, ? AS live_promotion_status, ? AS blockers_json",
            [payload["final_gate_status"], payload["live_promotion_status"], str(payload["blockers"])],
        )
    return path
