from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.proving.run_record import (
    PROVING_HISTORY_ROOT,
    PROVING_ROOT,
    ProvingRunRecord,
    record_to_dict,
)
from quant_os.proving.streaks import compute_streaks


def append_proving_record(record: ProvingRunRecord | dict[str, Any]) -> dict[str, Any]:
    payload = record_to_dict(record)
    PROVING_HISTORY_ROOT.mkdir(parents=True, exist_ok=True)
    stamp = payload["timestamp"].replace(":", "-").replace("+00:00", "Z")
    (PROVING_HISTORY_ROOT / f"{stamp}_{payload['run_id']}.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    history = load_proving_history()
    status = build_status(history)
    _write_status(status)
    return status


def load_proving_history(history_root: str | Path = PROVING_HISTORY_ROOT) -> list[dict[str, Any]]:
    root = Path(history_root)
    if not root.exists():
        return []
    records = []
    for path in sorted(root.glob("*.json")):
        try:
            records.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    records.sort(key=lambda item: item.get("timestamp", ""))
    return records


def build_status(history: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    records = history if history is not None else load_proving_history()
    streaks = compute_streaks(records)
    warning_runs = sum(1 for item in records if item.get("warnings"))
    latest = records[-1] if records else {}
    payload = {
        "status": "PASS" if records else "NOT_STARTED",
        "history_records_count": len(records),
        "latest_run_id": latest.get("run_id"),
        "latest_run_status": latest.get("run_status", "NOT_STARTED"),
        "streaks": streaks,
        "warning_runs": warning_runs,
        "unresolved_incidents": 0,
        "live_promotion_status": "LIVE_BLOCKED",
        "live_ready": False,
        "latest_report_path": "reports/proving/latest_status.md",
    }
    return payload


def write_proving_status(history: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    payload = build_status(history)
    _write_status(payload)
    return payload


def _write_status(payload: dict[str, Any]) -> None:
    PROVING_ROOT.mkdir(parents=True, exist_ok=True)
    (PROVING_ROOT / "latest_status.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    lines = [
        "# Proving Status",
        "",
        "Dry-run/simulation proving status. No live trading.",
        "",
        f"Status: {payload['status']}",
        f"History records: {payload['history_records_count']}",
        f"Current success streak: {payload['streaks']['current_success_streak']}",
        f"Current failure streak: {payload['streaks']['current_failure_streak']}",
        f"Live promotion: {payload['live_promotion_status']}",
    ]
    (PROVING_ROOT / "latest_status.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
