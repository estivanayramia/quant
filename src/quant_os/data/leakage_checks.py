from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from quant_os.data.dataset_manifest import DATASET_REPORT_ROOT
from quant_os.data.dataset_splits import build_dataset_splits


def run_leakage_checks(
    write: bool = True, splits_payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    splits = splits_payload or build_dataset_splits(write=True)
    failures: list[str] = []
    warnings: list[str] = []
    for item in splits.get("items", []):
        split_ranges = item["splits"]
        if ranges_overlap(split_ranges["train"], split_ranges["validation"]):
            failures.append(f"TRAIN_VALIDATION_OVERLAP:{item['timeframe']}:{item['symbol']}")
        if ranges_overlap(split_ranges["validation"], split_ranges["test"]):
            failures.append(f"VALIDATION_TEST_OVERLAP:{item['timeframe']}:{item['symbol']}")
        if ranges_overlap(split_ranges["train"], split_ranges["test"]):
            failures.append(f"TRAIN_TEST_OVERLAP:{item['timeframe']}:{item['symbol']}")
        for window in item.get("walk_forward", []):
            if not ordered_before(window["train"], window["test"]):
                failures.append(f"WALK_FORWARD_ORDER:{item['timeframe']}:{item['symbol']}")
        if not item.get("walk_forward"):
            warnings.append(f"NO_WALK_FORWARD_WINDOWS:{item['timeframe']}:{item['symbol']}")
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "FAIL" if failures else "WARN" if warnings else "PASS",
        "failures": failures,
        "warnings": warnings,
        "target_leakage": "NOT_APPLICABLE",
        "feature_leakage": "ROLLING_FEATURES_USE_CURRENT_OR_PRIOR_ROWS_IN_TESTS",
        "live_trading_enabled": False,
    }
    if write:
        _write_leakage(payload)
    return payload


def ranges_overlap(first: dict[str, Any], second: dict[str, Any]) -> bool:
    if first.get("rows", 0) == 0 or second.get("rows", 0) == 0:
        return False
    return int(first["start_index"]) <= int(second["end_index"]) and int(
        second["start_index"]
    ) <= int(first["end_index"])


def ordered_before(first: dict[str, Any], second: dict[str, Any]) -> bool:
    if first.get("rows", 0) == 0 or second.get("rows", 0) == 0:
        return False
    return int(first["end_index"]) < int(second["start_index"])


def _write_leakage(payload: dict[str, Any]) -> None:
    DATASET_REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    (DATASET_REPORT_ROOT / "latest_leakage_check.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8"
    )
    lines = [
        "# Dataset Leakage Check",
        "",
        "Offline split and leakage metadata. No live trading.",
        "",
        f"Status: {payload['status']}",
        f"Target leakage: {payload['target_leakage']}",
        "",
        "## Failures",
    ]
    lines.extend(f"- {failure}" for failure in (payload["failures"] or ["None"]))
    lines.extend(["", "## Warnings"])
    lines.extend(f"- {warning}" for warning in (payload["warnings"] or ["None"]))
    (DATASET_REPORT_ROOT / "latest_leakage_check.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
