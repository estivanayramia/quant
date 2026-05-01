from __future__ import annotations

from pathlib import Path

import duckdb

from quant_os.governance.live_attempt_registry import load_live_attempts


def rebuild_live_attempt_projection(
    db_path: str | Path = "data/read_models/read_models.duckdb",
) -> Path:
    attempts = load_live_attempts()
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(path)) as con:
        con.execute(
            "CREATE OR REPLACE TABLE live_canary_attempts "
            "(attempt_id VARCHAR, symbol VARCHAR, status VARCHAR, fake_mode BOOLEAN)"
        )
        for attempt in attempts:
            con.execute(
                "INSERT INTO live_canary_attempts VALUES (?, ?, ?, ?)",
                [
                    attempt.get("attempt_id"),
                    attempt.get("symbol"),
                    attempt.get("status"),
                    bool(attempt.get("fake_mode")),
                ],
            )
    return path
