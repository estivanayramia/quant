from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

REQUIRED_ORDERBOOK_COLUMNS = ("market_id", "token_id", "timestamp", "bid_price", "ask_price")


def summarize_pmxt_manifest(manifest_path: str | Path | None) -> dict[str, Any]:
    if manifest_path is None:
        return _empty("NOT_PROVIDED")
    path = Path(manifest_path)
    if not path.exists():
        return _empty("MISSING", path)

    payload = _read_manifest(path)
    files = payload.get("files", []) or []
    files_by_kind = dict(
        sorted(Counter(str(item.get("kind", "unknown")) for item in files).items())
    )
    orderbook_files = [item for item in files if item.get("kind") == "orderbook"]
    missing_columns = {
        str(item.get("path", "unknown")): [
            column for column in REQUIRED_ORDERBOOK_COLUMNS if column not in item.get("columns", [])
        ]
        for item in orderbook_files
    }
    missing_columns = {path_key: cols for path_key, cols in missing_columns.items() if cols}
    status = "PASS" if not missing_columns and files else "WARN"
    return {
        "source_id": "pmxt_orderbook_archives",
        "status": status,
        "path": str(path),
        "internet_required": False,
        "execution_authority_added": False,
        "files_count": len(files),
        "files_by_kind": files_by_kind,
        "rows": sum(int(item.get("rows", 0) or 0) for item in files),
        "required_orderbook_columns": list(REQUIRED_ORDERBOOK_COLUMNS),
        "missing_orderbook_columns": missing_columns,
    }


def _read_manifest(path: Path) -> dict[str, Any]:
    if path.suffix.lower() in {".yaml", ".yml"}:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return json.loads(path.read_text(encoding="utf-8"))


def _empty(status: str, path: Path | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source_id": "pmxt_orderbook_archives",
        "status": status,
        "internet_required": False,
        "execution_authority_added": False,
        "files_count": 0,
        "files_by_kind": {},
        "rows": 0,
        "required_orderbook_columns": list(REQUIRED_ORDERBOOK_COLUMNS),
        "missing_orderbook_columns": {},
    }
    if path is not None:
        payload["path"] = str(path)
    return payload
