from __future__ import annotations

import json
from typing import Any

import pandas as pd

from quant_os.data.column_mapping import CANONICAL_REQUIRED
from quant_os.data.data_license import validate_license_note
from quant_os.data.historical_cache import (
    NORMALIZED_LATEST,
    REPORT_ROOT,
    load_historical_config,
    now_utc,
)
from quant_os.data.historical_manifest import build_historical_manifest


def run_historical_quality(write: bool = True, frame: pd.DataFrame | None = None) -> dict[str, Any]:
    manifest = build_historical_manifest(write=True)
    data = frame if frame is not None else pd.read_parquet(NORMALIZED_LATEST)
    result = validate_historical_frame(data, manifest=manifest)
    payload = {
        "generated_at": now_utc(),
        "status": result["status"],
        "failures": result["failures"],
        "warnings": result["warnings"],
        "rows": int(len(data)),
        "manifest_dataset_id": manifest["dataset_id"],
        "source_name": manifest["source_name"],
        "license_note_present": bool(manifest.get("license_note")),
        "live_trading_enabled": False,
    }
    if write:
        _write_quality(payload)
    return payload


def validate_historical_frame(
    frame: pd.DataFrame, manifest: dict[str, Any] | None = None
) -> dict[str, Any]:
    config = load_historical_config()
    quality_config = config.get("quality", {})
    required = set(config.get("schema", {}).get("required_columns", CANONICAL_REQUIRED))
    failures: list[str] = []
    warnings: list[str] = []
    missing = sorted(required - set(frame.columns))
    if missing:
        failures.append(f"MISSING_COLUMNS:{','.join(missing)}")
        return {"status": "FAIL", "failures": failures, "warnings": warnings}
    data = frame.sort_values(["symbol", "timeframe", "timestamp"]).copy()
    if data[list(required)].isnull().any().any():
        failures.append("NULL_REQUIRED_VALUES")
    if data.duplicated(["symbol", "timeframe", "timestamp"]).any():
        failures.append("DUPLICATE_SYMBOL_TIMEFRAME_TIMESTAMP")
    if not (
        (data["high"] >= data[["open", "close"]].max(axis=1))
        & (data["low"] <= data[["open", "close"]].min(axis=1))
    ).all():
        failures.append("INVALID_OHLC")
    if (data[["open", "high", "low", "close"]] < 0).any().any():
        failures.append("NEGATIVE_PRICE")
    if (data["volume"] < 0).any():
        failures.append("NEGATIVE_VOLUME")
    timestamps = pd.to_datetime(data["timestamp"], utc=True, errors="coerce")
    if timestamps.isna().any():
        failures.append("TIMESTAMP_PARSE_FAILED")
    tolerance = pd.Timedelta(minutes=int(quality_config.get("future_timestamp_tolerance_minutes", 5)))
    if (timestamps > pd.Timestamp.now(tz="UTC") + tolerance).any():
        failures.append("FUTURE_TIMESTAMP_LEAKAGE")
    for _, group in data.groupby(["symbol", "timeframe"]):
        if not pd.to_datetime(group["timestamp"], utc=True).is_monotonic_increasing:
            failures.append("NON_MONOTONIC_TIME")
        if len(group) < int(quality_config.get("min_rows_warn", 500)):
            warnings.append(f"LOW_ROWS:{group['symbol'].iloc[0]}:{group['timeframe'].iloc[0]}")
    if manifest:
        warnings.extend(validate_license_note(manifest.get("license_note"), required=True))
        if not manifest.get("raw_sha256") or not manifest.get("normalized_sha256"):
            failures.append("FILE_HASH_MISSING")
    status = "FAIL" if failures else "WARN" if warnings else "PASS"
    return {"status": status, "failures": failures, "warnings": warnings}


def _write_quality(payload: dict[str, Any]) -> None:
    root = REPORT_ROOT / "quality"
    root.mkdir(parents=True, exist_ok=True)
    (root / "latest_quality.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8"
    )
    lines = [
        "# Historical Data Quality",
        "",
        "Local historical data validation. No live trading.",
        "",
        f"Status: {payload['status']}",
        f"Rows: {payload['rows']}",
        f"License note present: {payload['license_note_present']}",
        "",
        "## Failures",
    ]
    lines.extend(f"- {failure}" for failure in (payload["failures"] or ["None"]))
    lines.extend(["", "## Warnings"])
    lines.extend(f"- {warning}" for warning in (payload["warnings"] or ["None"]))
    (root / "latest_quality.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
