from __future__ import annotations

import csv
import importlib.util
from pathlib import Path
from typing import Any


def inspect_yahoo_reference(
    *,
    fixture_path: str | Path | None = None,
    optional_import: str = "yfinance",
) -> dict[str, Any]:
    return {
        "source_id": "yfinance",
        "classification": "runtime-safe",
        "read_only": True,
        "optional_import": optional_import,
        "optional_import_available": importlib.util.find_spec(optional_import) is not None,
        "network_required_for_fixture": False,
        "network_required_for_live_fetch": True,
        "execution_authority_added": False,
        "fixture": summarize_yahoo_fixture(fixture_path),
    }


def summarize_yahoo_fixture(fixture_path: str | Path | None) -> dict[str, Any]:
    if fixture_path is None:
        return {"status": "NOT_PROVIDED", "rows": 0, "symbols": []}
    path = Path(fixture_path)
    if not path.exists():
        return {"status": "MISSING", "path": str(path), "rows": 0, "symbols": []}

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        columns = list(reader.fieldnames or [])

    timestamp_column = _first_present(columns, ("timestamp", "date", "Date", "Datetime"))
    symbols = sorted({row.get("symbol", "UNKNOWN") or "UNKNOWN" for row in rows})
    timestamps = sorted(
        row[timestamp_column] for row in rows if timestamp_column and row.get(timestamp_column)
    )
    return {
        "status": "PASS",
        "path": str(path),
        "rows": len(rows),
        "columns": columns,
        "symbols": symbols,
        "start": timestamps[0] if timestamps else None,
        "end": timestamps[-1] if timestamps else None,
    }


def _first_present(columns: list[str], candidates: tuple[str, ...]) -> str | None:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None
