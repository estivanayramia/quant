from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from quant_os.data.dataset_manifest import DATASET_REPORT_ROOT, build_dataset_manifest

REQUIRED_COLUMNS = {
    "timestamp",
    "symbol",
    "timeframe",
    "open",
    "high",
    "low",
    "close",
    "volume",
}


def run_dataset_quality(
    dataset_root: str | Path = "data/demo_expanded", write: bool = True
) -> dict[str, Any]:
    manifest = build_dataset_manifest(dataset_root, write=False)
    failures: list[str] = []
    warnings: list[str] = []
    file_results = []
    regimes: set[str] = set()
    for item in manifest["files"]:
        path = Path(item["path"])
        frame = pd.read_parquet(path)
        result = validate_dataset_frame(frame)
        regimes.update(
            frame.get("regime", pd.Series(dtype=str)).dropna().astype(str).unique().tolist()
        )
        failures.extend(f"{path}:{reason}" for reason in result["failures"])
        warnings.extend(f"{path}:{reason}" for reason in result["warnings"])
        file_results.append({"path": str(path), **result})
    if len(manifest["symbols"]) < 3:
        warnings.append("LIMITED_SYMBOL_COVERAGE")
    if len(manifest["timeframes"]) < 2:
        warnings.append("LIMITED_TIMEFRAME_COVERAGE")
    if len(regimes) < 3:
        warnings.append("LIMITED_REGIME_COVERAGE")
    status = "FAIL" if failures else "WARN" if warnings else "PASS"
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": status,
        "failures": failures,
        "warnings": warnings,
        "files_checked": len(file_results),
        "symbols_count": len(manifest["symbols"]),
        "timeframes_count": len(manifest["timeframes"]),
        "regime_coverage": sorted(regimes),
        "file_results": file_results,
        "live_trading_enabled": False,
    }
    if write:
        _write_quality(payload)
    return payload


def validate_dataset_frame(frame: pd.DataFrame) -> dict[str, Any]:
    failures: list[str] = []
    warnings: list[str] = []
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        failures.append(f"MISSING_COLUMNS:{','.join(missing)}")
        return {"status": "FAIL", "failures": failures, "warnings": warnings, "rows": len(frame)}
    data = frame.sort_values(["symbol", "timeframe", "timestamp"]).copy()
    if data[list(REQUIRED_COLUMNS)].isnull().any().any():
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
    timestamps = pd.to_datetime(data["timestamp"], utc=True)
    if (timestamps > pd.Timestamp.now(tz="UTC") + pd.Timedelta(minutes=5)).any():
        failures.append("FUTURE_TIMESTAMP_LEAKAGE")
    for _, group in data.groupby(["symbol", "timeframe"]):
        if not pd.to_datetime(group["timestamp"], utc=True).is_monotonic_increasing:
            failures.append("NON_MONOTONIC_TIME")
        if len(group) < 500:
            warnings.append(f"LIMITED_ROWS:{group['symbol'].iloc[0]}:{group['timeframe'].iloc[0]}")
    status = "FAIL" if failures else "WARN" if warnings else "PASS"
    return {"status": status, "failures": failures, "warnings": warnings, "rows": len(frame)}


def _write_quality(payload: dict[str, Any]) -> None:
    DATASET_REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    (DATASET_REPORT_ROOT / "latest_quality.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8"
    )
    lines = [
        "# Dataset Quality",
        "",
        "Synthetic/offline data validation. No live trading.",
        "",
        f"Status: {payload['status']}",
        f"Files checked: {payload['files_checked']}",
        f"Regimes: {', '.join(payload['regime_coverage'])}",
        "",
        "## Failures",
    ]
    lines.extend(f"- {failure}" for failure in (payload["failures"] or ["None"]))
    lines.extend(["", "## Warnings"])
    lines.extend(f"- {warning}" for warning in (payload["warnings"] or ["None"]))
    (DATASET_REPORT_ROOT / "latest_quality.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
