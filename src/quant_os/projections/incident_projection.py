from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb


def rebuild_incident_projection(
    incidents: list[dict[str, Any]],
    db_path: str | Path = "data/read_models/quant_os.duckdb",
) -> Path:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS proving_incidents (
                incident_id VARCHAR,
                timestamp VARCHAR,
                severity VARCHAR,
                category VARCHAR,
                resolved BOOLEAN,
                payload_json VARCHAR
            )
            """
        )
        conn.execute("DELETE FROM proving_incidents")
        for incident in incidents:
            conn.execute(
                "INSERT INTO proving_incidents VALUES (?, ?, ?, ?, ?, ?)",
                [
                    incident.get("incident_id"),
                    incident.get("timestamp"),
                    incident.get("severity"),
                    incident.get("category"),
                    bool(incident.get("resolved")),
                    json.dumps(incident, sort_keys=True, default=str),
                ],
            )
    return path
