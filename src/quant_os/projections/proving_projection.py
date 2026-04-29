from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb


def rebuild_proving_projection(
    records: list[dict[str, Any]],
    db_path: str | Path = "data/read_models/quant_os.duckdb",
) -> Path:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS proving_runs (
                run_id VARCHAR,
                timestamp VARCHAR,
                run_status VARCHAR,
                top_strategy_id VARCHAR,
                evidence_score_status VARCHAR,
                payload_json VARCHAR
            )
            """
        )
        conn.execute("DELETE FROM proving_runs")
        for record in records:
            conn.execute(
                "INSERT INTO proving_runs VALUES (?, ?, ?, ?, ?, ?)",
                [
                    record.get("run_id"),
                    record.get("timestamp"),
                    record.get("run_status"),
                    record.get("top_strategy_id"),
                    record.get("evidence_score_status"),
                    json.dumps(record, sort_keys=True, default=str),
                ],
            )
    return path
