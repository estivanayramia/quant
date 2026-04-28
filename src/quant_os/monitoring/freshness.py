from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_os.monitoring.dryrun_history import load_dryrun_monitoring_config


def artifact_freshness(
    path: str | Path,
    *,
    warn_hours: float | None = None,
    fail_hours: float | None = None,
) -> dict[str, Any]:
    config = load_dryrun_monitoring_config()
    warn = float(warn_hours or config.get("freshness_warn_hours", 24))
    fail = float(fail_hours or config.get("freshness_fail_hours", 72))
    artifact = Path(path)
    if not artifact.exists():
        return {
            "path": str(artifact),
            "status": "UNAVAILABLE",
            "age_hours": None,
            "reason": "ARTIFACT_MISSING",
        }
    modified = datetime.fromtimestamp(artifact.stat().st_mtime, tz=UTC)
    age_hours = (datetime.now(UTC) - modified).total_seconds() / 3600
    status = "PASS"
    reason = "FRESH"
    if age_hours > fail:
        status = "FAIL"
        reason = "STALE_FAIL"
    elif age_hours > warn:
        status = "WARN"
        reason = "STALE_WARN"
    return {
        "path": str(artifact),
        "status": status,
        "age_hours": age_hours,
        "reason": reason,
        "modified_at": modified.isoformat(),
    }


def dryrun_freshness_summary() -> dict[str, Any]:
    paths = {
        "config": "freqtrade/user_data/config/config.dry-run.generated.json",
        "strategy": "freqtrade/user_data/strategies/QuantOSDryRunStrategy.py",
        "logs": "reports/freqtrade/logs/latest_logs.json",
        "operational_status": "reports/freqtrade/status/latest_operational_status.json",
        "reconciliation": "reports/freqtrade/reconciliation/latest_reconciliation.json",
    }
    checks = {name: artifact_freshness(path) for name, path in paths.items()}
    statuses = {check["status"] for check in checks.values()}
    status = (
        "FAIL" if "FAIL" in statuses else "WARN" if statuses & {"WARN", "UNAVAILABLE"} else "PASS"
    )
    return {"generated_at": datetime.now(UTC).isoformat(), "status": status, "checks": checks}
