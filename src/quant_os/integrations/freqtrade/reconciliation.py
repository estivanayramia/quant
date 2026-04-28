from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_os.data.loaders import load_yaml
from quant_os.integrations.freqtrade.artifacts import ensure_freqtrade_artifact_dirs
from quant_os.integrations.freqtrade.docker_ops import DockerOps
from quant_os.integrations.freqtrade.safety import FreqtradeSafetyError, validate_freqtrade_config


def reconcile_freqtrade() -> dict[str, object]:
    dirs = ensure_freqtrade_artifact_dirs()
    config_path = Path("freqtrade/user_data/config/config.dry-run.generated.json")
    strategy_path = Path("freqtrade/user_data/strategies/QuantOSDryRunStrategy.py")
    manifest_path = Path("reports/freqtrade/latest_manifest.json")
    logs_path = Path("reports/freqtrade/logs/latest_logs.json")
    checks: list[dict[str, object]] = []
    status = "PASS"

    def add(name: str, check_status: str, details: dict[str, Any] | None = None) -> None:
        nonlocal status
        checks.append({"name": name, "status": check_status, "details": details or {}})
        if check_status == "FAIL":
            status = "FAIL"
        elif check_status == "WARN" and status == "PASS":
            status = "WARN"

    if not config_path.exists():
        add("config_present", "FAIL")
    else:
        try:
            validate_freqtrade_config(config_path)
            add("config_safety", "PASS")
        except FreqtradeSafetyError as exc:
            add("config_safety", "FAIL", {"error": str(exc)})
    if not strategy_path.exists():
        add("strategy_present", "FAIL")
    else:
        add("strategy_hash", "PASS", {"sha256": _sha256(strategy_path)})
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected_hash = manifest.get("strategy_sha256")
        actual_hash = _sha256(strategy_path) if strategy_path.exists() else None
        if expected_hash and actual_hash and expected_hash != actual_hash:
            add("strategy_manifest_hash", "FAIL")
        else:
            add("strategy_manifest", "PASS" if manifest_path.exists() else "WARN")
    else:
        add("manifest_present", "WARN")
    _compare_risk_limits(config_path, add)
    docker = DockerOps()
    if not docker.docker_available():
        add("docker_available", "WARN")
    container_status = docker.get_container_status().status
    if container_status in {"UNAVAILABLE", "stopped", "UNKNOWN"}:
        add("container_status", "WARN", {"container_status": container_status})
    else:
        add("container_status", "PASS", {"container_status": container_status})
    if not logs_path.exists():
        add("logs_present", "WARN")
    else:
        logs = json.loads(logs_path.read_text(encoding="utf-8"))
        if _logs_indicate_live(logs):
            add("logs_live_mode", "FAIL")
        else:
            add("logs_live_mode", "PASS")
        if not logs.get("pairs"):
            add("pairs_detectable", "WARN")
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": status if checks else "UNAVAILABLE",
        "checks": checks,
        "dry_run_only": True,
        "live_trading_enabled": False,
    }
    _write_reports(payload, dirs["reconciliation_dir"])
    return payload


def _compare_risk_limits(config_path: Path, add) -> None:
    if not config_path.exists():
        return
    config = json.loads(config_path.read_text(encoding="utf-8"))
    risk = load_yaml("configs/risk_limits.yaml")
    if int(config.get("max_open_trades", 999)) > int(risk.get("max_open_positions", 1)):
        add("max_open_trades_vs_risk", "FAIL")
    else:
        add("max_open_trades_vs_risk", "PASS")
    if float(config.get("stake_amount", 999999)) > float(risk.get("max_order_notional", 25)):
        add("stake_amount_vs_risk", "FAIL")
    else:
        add("stake_amount_vs_risk", "PASS")


def _logs_indicate_live(logs: dict[str, Any]) -> bool:
    entries = logs.get("entries", [])
    raw = "\n".join(str(entry.get("raw", "")) for entry in entries).lower()
    return "dry_run false" in raw or "dry-run false" in raw or "live mode" in raw


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_reports(payload: dict[str, object], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "latest_reconciliation.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    lines = [
        "# Freqtrade Reconciliation",
        "",
        f"Status: {payload['status']}",
        "",
        "Dry-run only. No live trading.",
        "",
    ]
    for check in payload["checks"]:
        lines.append(f"- {check['status']}: {check['name']} {check['details']}")
    (output_dir / "latest_reconciliation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
