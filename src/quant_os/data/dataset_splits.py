from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from quant_os.data.dataset_manifest import DATASET_REPORT_ROOT, build_dataset_manifest
from quant_os.data.loaders import load_yaml


def build_dataset_splits(
    dataset_root: str | Path = "data/demo_expanded",
    config_path: str | Path = "configs/datasets.yaml",
    write: bool = True,
) -> dict[str, Any]:
    manifest = build_dataset_manifest(dataset_root, write=False)
    config = load_yaml(config_path) if Path(config_path).exists() else {}
    split_config = config.get("splits", {})
    train_ratio = float(split_config.get("train_ratio", 0.6))
    validation_ratio = float(split_config.get("validation_ratio", 0.2))
    purge_gap = int(split_config.get("purge_gap_bars", 1))
    min_wf = int(split_config.get("walk_forward_min_splits", 3))
    split_items = []
    for item in manifest["files"]:
        frame = pd.read_parquet(item["path"]).sort_values("timestamp").reset_index(drop=True)
        split_items.append(
            {
                "symbol": item["symbol"],
                "timeframe": item["timeframe"],
                "rows": len(frame),
                "splits": split_frame_ranges(frame, train_ratio, validation_ratio, purge_gap),
                "walk_forward": walk_forward_ranges(frame, min_wf, purge_gap),
            }
        )
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "PASS" if split_items else "UNAVAILABLE",
        "purge_gap_bars": purge_gap,
        "items": split_items,
        "live_trading_enabled": False,
    }
    if write:
        _write_splits(payload)
    return payload


def split_frame_ranges(
    frame: pd.DataFrame,
    train_ratio: float = 0.6,
    validation_ratio: float = 0.2,
    purge_gap_bars: int = 1,
) -> dict[str, dict[str, Any]]:
    rows = len(frame)
    train_end = max(0, int(rows * train_ratio) - 1)
    validation_start = min(rows, train_end + 1 + purge_gap_bars)
    validation_end = max(validation_start, int(rows * (train_ratio + validation_ratio)) - 1)
    test_start = min(rows, validation_end + 1 + purge_gap_bars)
    test_end = rows - 1
    return {
        "train": _range_payload(frame, 0, train_end),
        "validation": _range_payload(frame, validation_start, validation_end),
        "test": _range_payload(frame, test_start, test_end),
    }


def walk_forward_ranges(
    frame: pd.DataFrame,
    min_splits: int = 3,
    purge_gap_bars: int = 1,
) -> list[dict[str, Any]]:
    rows = len(frame)
    if rows < 60:
        return []
    train_size = max(20, rows // (min_splits + 2))
    test_size = max(10, (rows - train_size) // (min_splits + 1))
    ranges = []
    start = 0
    for split in range(1, min_splits + 1):
        train_start = start
        train_end = train_start + train_size - 1
        test_start = train_end + 1 + purge_gap_bars
        test_end = min(rows - 1, test_start + test_size - 1)
        if test_start >= rows or test_end <= test_start:
            break
        ranges.append(
            {
                "split": split,
                "train": _range_payload(frame, train_start, train_end),
                "test": _range_payload(frame, test_start, test_end),
            }
        )
        start += test_size
    return ranges


def _range_payload(frame: pd.DataFrame, start: int, end: int) -> dict[str, Any]:
    if len(frame) == 0 or start >= len(frame) or end < start:
        return {"start_index": None, "end_index": None, "start": None, "end": None, "rows": 0}
    end = min(end, len(frame) - 1)
    return {
        "start_index": int(start),
        "end_index": int(end),
        "start": pd.Timestamp(frame.loc[start, "timestamp"]).isoformat(),
        "end": pd.Timestamp(frame.loc[end, "timestamp"]).isoformat(),
        "rows": int(end - start + 1),
    }


def _write_splits(payload: dict[str, Any]) -> None:
    DATASET_REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    (DATASET_REPORT_ROOT / "latest_splits.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8"
    )
    lines = [
        "# Dataset Splits",
        "",
        "Train/validation/test and walk-forward metadata. No live trading.",
        "",
        f"Status: {payload['status']}",
        f"Items: {len(payload['items'])}",
        f"Purge gap bars: {payload['purge_gap_bars']}",
    ]
    (DATASET_REPORT_ROOT / "latest_splits.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
