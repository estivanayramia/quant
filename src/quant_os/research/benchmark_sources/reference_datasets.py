from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

REFERENCE_DATASET_SPECS = {
    "prediction_market_analysis": {
        "classification": "offline-cache-only",
        "expected_formats": ["parquet"],
        "required_tables": ["markets", "trades"],
    },
    "polymarket_data": {
        "classification": "offline-cache-only",
        "expected_formats": ["parquet"],
        "required_tables": ["markets", "trades", "quant"],
    },
}


def summarize_reference_datasets(manifest_path: str | Path | None) -> dict[str, Any]:
    if manifest_path is None:
        return _empty("NOT_PROVIDED")
    path = Path(manifest_path)
    if not path.exists():
        return _empty("MISSING", path)

    payload = _read_manifest(path)
    datasets = payload.get("datasets", []) or []
    datasets_by_source = dict(
        sorted(Counter(str(item.get("source_id", "unknown")) for item in datasets).items())
    )
    unknown_sources = sorted(
        source_id for source_id in datasets_by_source if source_id not in REFERENCE_DATASET_SPECS
    )
    return {
        "source_id": "reference_datasets",
        "status": "PASS" if datasets and not unknown_sources else "WARN",
        "path": str(path),
        "internet_required": False,
        "execution_authority_added": False,
        "datasets_count": len(datasets),
        "datasets_by_source": datasets_by_source,
        "unknown_sources": unknown_sources,
        "total_rows": sum(int(item.get("rows", 0) or 0) for item in datasets),
        "total_size_gb": round(sum(float(item.get("size_gb", 0.0) or 0.0) for item in datasets), 4),
    }


def _read_manifest(path: Path) -> dict[str, Any]:
    if path.suffix.lower() in {".yaml", ".yml"}:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return json.loads(path.read_text(encoding="utf-8"))


def _empty(status: str, path: Path | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source_id": "reference_datasets",
        "status": status,
        "internet_required": False,
        "execution_authority_added": False,
        "datasets_count": 0,
        "datasets_by_source": {},
        "unknown_sources": [],
        "total_rows": 0,
        "total_size_gb": 0.0,
    }
    if path is not None:
        payload["path"] = str(path)
    return payload
