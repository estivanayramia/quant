"""Verify local DuckDB CSV/Parquet inspection and the duckdb_mcp extension.

This script creates a tiny ignored sample under data/external/duckdb_verify and
queries it with DuckDB. It does not touch live trading code or credentials.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DIR = REPO_ROOT / "data" / "external" / "duckdb_verify"
CSV_PATH = SAMPLE_DIR / "sample_prediction_market_prices.csv"
PARQUET_PATH = SAMPLE_DIR / "sample_prediction_market_prices.parquet"


def sql_path(path: Path) -> str:
    return path.as_posix().replace("'", "''")


def ensure_sample_files() -> None:
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    if not CSV_PATH.exists():
        rows = [
            {"ts": "2026-05-06T00:00:00Z", "market_id": "demo-btc-up", "price": "0.47"},
            {"ts": "2026-05-06T00:01:00Z", "market_id": "demo-btc-up", "price": "0.49"},
            {"ts": "2026-05-06T00:02:00Z", "market_id": "demo-eth-up", "price": "0.53"},
        ]
        with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["ts", "market_id", "price"])
            writer.writeheader()
            writer.writerows(rows)


def main() -> int:
    ensure_sample_files()
    con = duckdb.connect()
    version = con.execute("SELECT version()").fetchone()[0]

    con.execute("INSTALL duckdb_mcp FROM community")
    con.execute("LOAD duckdb_mcp")
    mcp_functions = con.execute(
        "SELECT COUNT(*) FROM duckdb_functions() WHERE function_name LIKE 'mcp_%'"
    ).fetchone()[0]

    csv_summary = con.execute(
        f"""
        SELECT market_id, COUNT(*) AS rows, ROUND(AVG(price), 4) AS avg_price
        FROM read_csv_auto('{sql_path(CSV_PATH)}')
        GROUP BY market_id
        ORDER BY market_id
        """
    ).fetchall()

    if not PARQUET_PATH.exists():
        con.execute(
            f"""
            COPY (
                SELECT * FROM read_csv_auto('{sql_path(CSV_PATH)}')
            )
            TO '{sql_path(PARQUET_PATH)}' (FORMAT PARQUET)
            """
        )

    parquet_summary = con.execute(
        f"""
        SELECT COUNT(*) AS rows, MIN(price) AS min_price, MAX(price) AS max_price
        FROM read_parquet('{sql_path(PARQUET_PATH)}')
        """
    ).fetchone()

    print(
        json.dumps(
            {
                "duckdb_version": version,
                "duckdb_mcp_functions": mcp_functions,
                "csv_path": str(CSV_PATH.relative_to(REPO_ROOT)),
                "csv_summary": csv_summary,
                "parquet_path": str(PARQUET_PATH.relative_to(REPO_ROOT)),
                "parquet_summary": {
                    "rows": parquet_summary[0],
                    "min_price": parquet_summary[1],
                    "max_price": parquet_summary[2],
                },
            },
            indent=2,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
