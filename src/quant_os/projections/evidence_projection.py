from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import pandas as pd


def rebuild_evidence_projection(
    evidence: dict[str, Any],
    db_path: str | Path = "data/read_models/quant_os.duckdb",
) -> Path:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "generated_at": evidence.get("generated_at"),
        "final_evidence_status": evidence.get("final_evidence_status"),
        "live_promotion_status": evidence.get("live_promotion_status"),
        "raw_score": evidence.get("raw_score"),
        "data_quality_status": evidence.get("data_quality_status"),
        "leakage_status": evidence.get("leakage_status"),
    }
    con = duckdb.connect(str(path))
    try:
        con.execute("drop table if exists evidence_score")
        con.register("evidence_score_df", pd.DataFrame([row]))
        con.execute("create table evidence_score as select * from evidence_score_df")
    finally:
        con.close()
    return path
