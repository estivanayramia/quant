from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from quant_os.core.ids import deterministic_id
from quant_os.data.loaders import load_yaml
from quant_os.integrations.freqtrade.safety import FreqtradeSafetyError, validate_freqtrade_config

DRYRUN_ROOT = Path("reports/dryrun")
DRYRUN_HISTORY_DIR = DRYRUN_ROOT / "history"
GENERATED_CONFIG = Path("freqtrade/user_data/config/config.dry-run.generated.json")
GENERATED_STRATEGY = Path("freqtrade/user_data/strategies/QuantOSDryRunStrategy.py")
LATEST_AUTONOMY = Path("reports/autonomy/latest_run.json")
LATEST_OPERATIONAL_STATUS = Path("reports/freqtrade/status/latest_operational_status.json")
LATEST_RECONCILIATION = Path("reports/freqtrade/reconciliation/latest_reconciliation.json")
LATEST_LOGS = Path("reports/freqtrade/logs/latest_logs.json")

DEFAULT_MONITORING_CONFIG: dict[str, Any] = {
    "enabled": True,
    "history_window_days": 30,
    "freshness_warn_hours": 24,
    "freshness_fail_hours": 72,
    "divergence_warn_threshold": 0.25,
    "divergence_fail_threshold": 0.50,
    "live_promotion_allowed": False,
}


def load_dryrun_monitoring_config(
    path: str | Path = "configs/dryrun_monitoring.yaml",
) -> dict[str, Any]:
    config = DEFAULT_MONITORING_CONFIG.copy()
    config_path = Path(path)
    if config_path.exists():
        config.update(load_yaml(config_path))
    return config


def ensure_dryrun_monitoring_dirs() -> dict[str, Path]:
    DRYRUN_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    return {"root": DRYRUN_ROOT, "history": DRYRUN_HISTORY_DIR}


def build_history_record(source: str = "manual") -> dict[str, Any]:
    timestamp = datetime.now(UTC).isoformat()
    autonomy = _read_json(LATEST_AUTONOMY) or {}
    status = _read_json(LATEST_OPERATIONAL_STATUS) or {}
    reconciliation = _read_json(LATEST_RECONCILIATION) or {}
    logs = _read_json(LATEST_LOGS) or {}
    config_payload = _read_json(GENERATED_CONFIG) or {}
    safety = _safety_status(GENERATED_CONFIG)
    config_hash = _sha256(GENERATED_CONFIG)
    strategy_hash = _sha256(GENERATED_STRATEGY)
    warnings = _collect_warnings(reconciliation, logs, safety)
    errors = _collect_errors(reconciliation, logs, safety)
    blockers = _collect_blockers(reconciliation, safety, config_payload)
    run_id = deterministic_id(
        "dryrun", source, timestamp, config_hash or "", strategy_hash or "", length=20
    )
    return {
        "run_id": run_id,
        "timestamp": timestamp,
        "source": source,
        "quantos_backtest_summary": autonomy.get("backtest_summary", {}),
        "quantos_shadow_summary": autonomy.get("shadow_summary", {}),
        "quantos_tournament_summary": autonomy.get("tournament_summary", {}),
        "freqtrade_status_summary": status,
        "freqtrade_reconciliation_status": reconciliation.get("status", "UNAVAILABLE"),
        "freqtrade_log_summary": {
            "line_count": logs.get("line_count", 0),
            "warnings": logs.get("warnings", 0),
            "errors": logs.get("errors", 0),
            "pairs": logs.get("pairs", []),
            "dry_run_indicators": logs.get("dry_run_indicators", 0),
        },
        "config_hash": config_hash,
        "strategy_hash": strategy_hash,
        "safety_guard_status": safety,
        "live_trading_enabled": bool(config_payload.get("live_trading_allowed", False)),
        "dry_run": config_payload.get("dry_run"),
        "warnings": warnings,
        "errors": errors,
        "blockers": blockers,
    }


def append_history_record(record: dict[str, Any] | None = None) -> dict[str, Any]:
    dirs = ensure_dryrun_monitoring_dirs()
    record = record or build_history_record()
    stamp = _safe_stamp(str(record["timestamp"]))
    history_path = dirs["history"] / f"{stamp}-{record['run_id']}.json"
    history_path.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
    records = load_history_records()
    latest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "records_count": len(records),
        "latest_record": record,
        "records": records,
    }
    (dirs["root"] / "latest_history.json").write_text(
        json.dumps(latest, indent=2, sort_keys=True), encoding="utf-8"
    )
    return latest


def load_history_records(window_days: int | None = None) -> list[dict[str, Any]]:
    ensure_dryrun_monitoring_dirs()
    cutoff = None
    if window_days is not None:
        cutoff = datetime.now(UTC) - timedelta(days=window_days)
    records: list[dict[str, Any]] = []
    for path in sorted(DRYRUN_HISTORY_DIR.glob("*.json")):
        payload = _read_json(path)
        if not payload:
            continue
        timestamp = _parse_timestamp(str(payload.get("timestamp", "")))
        if cutoff and timestamp and timestamp < cutoff:
            continue
        records.append(payload)
    return records


def _safety_status(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        return {"status": "UNAVAILABLE", "passed": False, "reasons": ["CONFIG_MISSING"]}
    try:
        result = validate_freqtrade_config(config_path)
    except FreqtradeSafetyError as exc:
        return {"status": "FAIL", "passed": False, "reasons": str(exc).split(";")}
    return {"status": "PASS", "passed": result.passed, "reasons": result.reasons}


def _collect_warnings(
    reconciliation: dict[str, Any], logs: dict[str, Any], safety: dict[str, Any]
) -> list[str]:
    warnings = [
        str(check.get("name"))
        for check in reconciliation.get("checks", [])
        if check.get("status") == "WARN"
    ]
    if int(logs.get("warnings", 0) or 0) > 0:
        warnings.append("FREQTRADE_LOG_WARNINGS")
    if safety.get("status") == "UNAVAILABLE":
        warnings.append("SAFETY_GUARD_UNAVAILABLE")
    return warnings


def _collect_errors(
    reconciliation: dict[str, Any], logs: dict[str, Any], safety: dict[str, Any]
) -> list[str]:
    errors = [
        str(check.get("name"))
        for check in reconciliation.get("checks", [])
        if check.get("status") == "FAIL"
    ]
    if int(logs.get("errors", 0) or 0) > 0:
        errors.append("FREQTRADE_LOG_ERRORS")
    if safety.get("status") == "FAIL":
        errors.extend(str(reason) for reason in safety.get("reasons", []))
    return errors


def _collect_blockers(
    reconciliation: dict[str, Any], safety: dict[str, Any], config_payload: dict[str, Any]
) -> list[str]:
    blockers = _collect_errors(reconciliation, {}, safety)
    if config_payload.get("dry_run") is False:
        blockers.append("DRY_RUN_FALSE")
    if config_payload.get("live_trading_allowed") is True:
        blockers.append("LIVE_TRADING_ALLOWED")
    return sorted(set(blockers))


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_stamp(timestamp: str) -> str:
    return timestamp.replace(":", "-").replace("+00:00", "Z")


def _parse_timestamp(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
