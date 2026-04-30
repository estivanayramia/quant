from __future__ import annotations

from pathlib import Path

import duckdb

from quant_os.canary.permissions_import import validate_latest_permission_manifest


def rebuild_permission_projection(db_path: str | Path = "data/read_models/read_models.duckdb") -> Path:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = validate_latest_permission_manifest()
    with duckdb.connect(str(path)) as conn:
        conn.execute(
            "CREATE OR REPLACE TABLE canary_permission_manifest AS SELECT ? AS status, ? AS scopes_json, ? AS blockers_json",
            [
                payload["status"],
                str(payload.get("normalized_scope_list", [])),
                str(payload.get("blockers", [])),
            ],
        )
    return path
