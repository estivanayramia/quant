from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb


def rebuild_evidence_projection(
    payload: dict[str, Any],
    db_path: str | Path = "data/read_models/quant_os.duckdb",
) -> Path:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS evidence_scores (
                generated_at VARCHAR,
                status VARCHAR,
                live_promotion_status VARCHAR,
                payload_json VARCHAR
            )
            """
        )
        conn.execute("DELETE FROM evidence_scores")
        conn.execute(
            "INSERT INTO evidence_scores VALUES (?, ?, ?, ?)",
            [
                payload.get("generated_at"),
                payload.get("final_evidence_status"),
                payload.get("live_promotion_status"),
                json.dumps(payload, sort_keys=True, default=str),
            ],
        )
    return path


def rebuild_historical_evidence_projection(
    payload: dict[str, Any],
    db_path: str | Path = "data/read_models/quant_os.duckdb",
) -> Path:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS historical_evidence (
                generated_at VARCHAR,
                status VARCHAR,
                live_promotion_status VARCHAR,
                payload_json VARCHAR
            )
            """
        )
        conn.execute("DELETE FROM historical_evidence")
        conn.execute(
            "INSERT INTO historical_evidence VALUES (?, ?, ?, ?)",
            [
                payload.get("generated_at"),
                payload.get("final_evidence_status"),
                payload.get("live_promotion_status"),
                json.dumps(payload, sort_keys=True, default=str),
            ],
        )
    return path
