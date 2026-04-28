from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from quant_os.data.data_license import DEFAULT_LICENSE_NOTE
from quant_os.data.historical_cache import (
    NORMALIZED_LATEST,
    REPORT_ROOT,
    SCHEMA_VERSION,
    ensure_historical_dirs,
    latest_import_record,
    now_utc,
    read_json,
    sha256_file,
    write_json,
)


def build_historical_manifest(write: bool = True) -> dict[str, Any]:
    ensure_historical_dirs()
    if not NORMALIZED_LATEST.exists():
        from quant_os.data.historical_import import import_historical_csv

        import_historical_csv()
    import_record = latest_import_record() or {}
    frame = pd.read_parquet(NORMALIZED_LATEST)
    raw_path = Path(import_record.get("raw_path", ""))
    normalized_hash = sha256_file(NORMALIZED_LATEST)
    symbols = sorted(frame["symbol"].dropna().astype(str).unique().tolist())
    timeframes = sorted(frame["timeframe"].dropna().astype(str).unique().tolist())
    payload = {
        "dataset_id": _dataset_id(normalized_hash),
        "source_type": import_record.get("source_type", "user_provided_file"),
        "source_name": import_record.get("source_name", "fixture_local"),
        "license_note": import_record.get("license_note", DEFAULT_LICENSE_NOTE),
        "imported_at": import_record.get("imported_at"),
        "normalized_at": _read_normalized_at(),
        "generated_at": now_utc(),
        "symbols": symbols,
        "timeframes": timeframes,
        "rows": int(len(frame)),
        "date_ranges": _date_ranges(frame),
        "raw_file": str(raw_path) if raw_path else None,
        "raw_sha256": sha256_file(raw_path) if raw_path.exists() else import_record.get("raw_sha256"),
        "normalized_file": str(NORMALIZED_LATEST),
        "normalized_sha256": normalized_hash,
        "schema_version": SCHEMA_VERSION,
        "column_mapping": import_record.get("column_mapping", {}),
        "caveats": [
            "Historical imports are local/cache-first research inputs only.",
            "Historical data does not imply live-trading readiness.",
            "Verify source licensing before using user-provided data.",
        ],
        "generated_by": "quant_os_phase9_historical_ingestion",
        "status": "PASS",
        "live_trading_enabled": False,
    }
    if write:
        _write_manifest(payload)
    return payload


def _dataset_id(normalized_hash: str) -> str:
    return "historical_" + normalized_hash[:20]


def _read_normalized_at() -> str | None:
    path = Path("data/historical/normalized/latest_normalized.json")
    return read_json(path).get("normalized_at") if path.exists() else None


def _date_ranges(frame: pd.DataFrame) -> dict[str, dict[str, str]]:
    ranges = {}
    for (symbol, timeframe), group in frame.groupby(["symbol", "timeframe"]):
        timestamps = pd.to_datetime(group["timestamp"], utc=True)
        ranges[f"{symbol}:{timeframe}"] = {
            "start": timestamps.min().isoformat(),
            "end": timestamps.max().isoformat(),
            "rows": str(len(group)),
        }
    return ranges


def _write_manifest(payload: dict[str, Any]) -> None:
    root = REPORT_ROOT / "manifests"
    root.mkdir(parents=True, exist_ok=True)
    write_json(root / "latest_manifest.json", payload)
    lines = [
        "# Historical Data Manifest",
        "",
        "Local/cache-first historical data. No live trading.",
        "",
        f"Dataset ID: {payload['dataset_id']}",
        f"Source: {payload['source_name']} ({payload['source_type']})",
        f"Rows: {payload['rows']}",
        f"Symbols: {', '.join(payload['symbols'])}",
        f"Timeframes: {', '.join(payload['timeframes'])}",
        f"License note: {payload['license_note']}",
        "",
        "## Caveats",
    ]
    lines.extend(f"- {item}" for item in payload["caveats"])
    (root / "latest_manifest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
