from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from quant_os.data.expanded_demo_data import SCHEMA_VERSION, seed_expanded_demo_data
from quant_os.projections.dataset_projection import rebuild_dataset_projection

DATASET_ROOT = Path("data/demo_expanded")
DATASET_REPORT_ROOT = Path("reports/datasets")


def build_dataset_manifest(
    dataset_root: str | Path = DATASET_ROOT, write: bool = True
) -> dict[str, Any]:
    root = Path(dataset_root)
    if not list(root.glob("timeframe=*/symbol=*/ohlcv.parquet")):
        seed_expanded_demo_data(root)
    files = []
    symbols: set[str] = set()
    timeframes: set[str] = set()
    total_rows = 0
    for path in sorted(root.glob("timeframe=*/symbol=*/ohlcv.parquet")):
        frame = pd.read_parquet(path)
        symbol = str(frame["symbol"].iloc[0])
        timeframe = str(frame["timeframe"].iloc[0])
        symbols.add(symbol)
        timeframes.add(timeframe)
        total_rows += len(frame)
        files.append(
            {
                "path": str(path),
                "sha256": _sha256(path),
                "rows": len(frame),
                "symbol": symbol,
                "timeframe": timeframe,
                "start": pd.Timestamp(frame["timestamp"].min()).isoformat(),
                "end": pd.Timestamp(frame["timestamp"].max()).isoformat(),
                "columns": frame.columns.tolist(),
            }
        )
    payload = {
        "dataset_id": _dataset_id(files),
        "generated_at": datetime.now(UTC).isoformat(),
        "generator_version": "expanded_demo_data_v1",
        "random_seed": 42,
        "symbols": sorted(symbols),
        "timeframes": sorted(timeframes),
        "rows": total_rows,
        "files": files,
        "schema_version": SCHEMA_VERSION,
        "data_source": "synthetic_demo",
        "caveat": "Synthetic offline demo data. Not real market data.",
        "status": "PASS" if files else "UNAVAILABLE",
    }
    if write:
        _write_manifest(payload)
        rebuild_dataset_projection(payload)
    return payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dataset_id(files: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for item in files:
        digest.update(str(item["path"]).encode("utf-8"))
        digest.update(str(item["sha256"]).encode("utf-8"))
    return "dataset_" + digest.hexdigest()[:20]


def _write_manifest(payload: dict[str, Any]) -> None:
    DATASET_REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    (DATASET_REPORT_ROOT / "latest_manifest.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8"
    )
    lines = [
        "# Dataset Manifest",
        "",
        "Synthetic offline demo data. Not real market data.",
        "",
        f"Dataset ID: {payload['dataset_id']}",
        f"Rows: {payload['rows']}",
        f"Symbols: {', '.join(payload['symbols'])}",
        f"Timeframes: {', '.join(payload['timeframes'])}",
        "",
        "## Files",
    ]
    lines.extend(
        f"- {item['timeframe']} {item['symbol']}: rows={item['rows']} sha256={item['sha256'][:12]}"
        for item in payload["files"]
    )
    (DATASET_REPORT_ROOT / "latest_manifest.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
