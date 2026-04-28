from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import pandas as pd


def rebuild_dataset_projection(
    manifest: dict[str, Any],
    db_path: str | Path = "data/read_models/quant_os.duckdb",
) -> Path:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "dataset_id": manifest["dataset_id"],
            "symbol": item["symbol"],
            "timeframe": item["timeframe"],
            "rows": item["rows"],
            "sha256": item["sha256"],
            "path": item["path"],
        }
        for item in manifest.get("files", [])
    ]
    con = duckdb.connect(str(path))
    try:
        con.execute("drop table if exists dataset_manifest")
        con.register("dataset_manifest_df", pd.DataFrame(rows))
        con.execute("create table dataset_manifest as select * from dataset_manifest_df")
    finally:
        con.close()
    return path
