from __future__ import annotations

from pathlib import Path

import duckdb

from quant_os.canary.approvals import load_approvals


def rebuild_approval_projection(db_path: str | Path = "data/read_models/read_models.duckdb") -> Path:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    approvals = load_approvals()
    rows = [record.model_dump(mode="json") for record in approvals]
    with duckdb.connect(str(path)) as conn:
        conn.execute(
            "CREATE OR REPLACE TABLE canary_approvals (approval_id VARCHAR, revoked BOOLEAN, expiry VARCHAR)"
        )
        if rows:
            conn.executemany(
                "INSERT INTO canary_approvals VALUES (?, ?, ?)",
                [(row["approval_id"], row["revoked"], row["expiry"]) for row in rows],
            )
    return path
