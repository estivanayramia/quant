from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_ARTIFACTS = {
    "autonomy_report": "reports/autonomy/latest_run.json",
    "dataset_manifest": "reports/datasets/latest_manifest.json",
    "historical_manifest": "reports/historical/manifests/latest_manifest.json",
    "dryrun_report": "reports/dryrun/latest_monitoring_report.json",
    "trade_reconciliation": "reports/freqtrade/trades/latest_trade_reconciliation.json",
    "leaderboard": "reports/strategy/leaderboard/latest_leaderboard.json",
}


def evaluate_freshness(
    *,
    artifacts: dict[str, str] | None = None,
    warn_hours: float = 24.0,
    fail_hours: float = 72.0,
) -> dict[str, Any]:
    artifacts = artifacts or DEFAULT_ARTIFACTS
    now = datetime.now(UTC)
    warnings: list[str] = []
    failures: list[str] = []
    details = {}
    for name, raw_path in artifacts.items():
        path = Path(raw_path)
        if not path.exists():
            warnings.append(f"MISSING_ARTIFACT:{name}")
            details[name] = {"path": raw_path, "status": "MISSING"}
            continue
        age_hours = (now - datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)).total_seconds() / 3600
        status = "PASS"
        if age_hours > fail_hours:
            failures.append(f"STALE_ARTIFACT_FAIL:{name}")
            status = "FAIL"
        elif age_hours > warn_hours:
            warnings.append(f"STALE_ARTIFACT_WARN:{name}")
            status = "WARN"
        details[name] = {"path": raw_path, "age_hours": age_hours, "status": status}
    return {
        "status": "FAIL" if failures else "WARN" if warnings else "PASS",
        "warnings": warnings,
        "failures": failures,
        "details": details,
    }
