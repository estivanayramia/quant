from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_os.monitoring.dryrun_comparison import build_dryrun_comparison
from quant_os.monitoring.dryrun_history import (
    DRYRUN_ROOT,
    GENERATED_CONFIG,
    GENERATED_STRATEGY,
    LATEST_LOGS,
    load_dryrun_monitoring_config,
)


def check_dryrun_divergence(write: bool = True) -> dict[str, Any]:
    config = load_dryrun_monitoring_config()
    checks: list[dict[str, Any]] = []

    def add(name: str, status: str, details: dict[str, Any] | None = None) -> None:
        checks.append({"name": name, "status": status, "details": details or {}})

    if not GENERATED_CONFIG.exists():
        add("config_present", "FAIL", {"path": str(GENERATED_CONFIG)})
    if not GENERATED_STRATEGY.exists():
        add("strategy_present", "FAIL", {"path": str(GENERATED_STRATEGY)})

    comparison = build_dryrun_comparison(write=True)
    for check in comparison["checks"]:
        if check["status"] == "FAIL":
            add(f"comparison_{check['name']}", "FAIL", check.get("details", {}))
        elif check["status"] in {"WARN", "UNAVAILABLE"}:
            add(f"comparison_{check['name']}", "WARN", check.get("details", {}))

    _check_strategy_manifest_hash(add)
    _check_live_danger_logs(add)

    fail_count = sum(1 for check in checks if check["status"] == "FAIL")
    warn_count = sum(1 for check in checks if check["status"] == "WARN")
    total = max(len(checks), 1)
    fail_threshold = float(config.get("divergence_fail_threshold", 0.5))
    score = 1.0 if fail_count else min(warn_count / total, fail_threshold - 0.01)
    status = "PASS"
    if fail_count or score >= fail_threshold:
        status = "FAIL"
    elif warn_count or score >= float(config.get("divergence_warn_threshold", 0.25)):
        status = "WARN"
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": status,
        "score": score,
        "checks": checks,
        "failures": [check for check in checks if check["status"] == "FAIL"],
        "warnings": [check for check in checks if check["status"] == "WARN"],
        "dry_run_only": True,
        "live_trading_enabled": False,
    }
    if write:
        (DRYRUN_ROOT / "latest_divergence.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
        )
    return payload


def _check_strategy_manifest_hash(add) -> None:
    manifest_path = Path("reports/freqtrade/latest_manifest.json")
    if not manifest_path.exists() or not GENERATED_STRATEGY.exists():
        add("strategy_hash_manifest_available", "WARN")
        return
    manifest = _read_json(manifest_path) or {}
    expected = manifest.get("strategy_sha256")
    actual = _sha256(GENERATED_STRATEGY)
    if not expected:
        add("strategy_hash_manifest_available", "WARN", {"actual": actual})
        return
    add(
        "strategy_hash_matches_manifest",
        "PASS" if expected == actual else "FAIL",
        {"expected": expected, "actual": actual},
    )


def _check_live_danger_logs(add) -> None:
    logs = _read_json(LATEST_LOGS)
    if logs is None:
        add("logs_available", "WARN")
        return
    text = json.dumps(logs).lower()
    matches = [
        pattern
        for pattern in [
            "dry_run false",
            "dry-run false",
            '"dry_run": false',
            "live mode",
            "live trading enabled",
            "real order",
        ]
        if pattern in text
    ]
    add("logs_live_danger_absent", "PASS" if not matches else "FAIL", {"matches": matches})


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
