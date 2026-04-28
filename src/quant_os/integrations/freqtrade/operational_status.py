from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from quant_os.integrations.freqtrade.artifacts import ensure_freqtrade_artifact_dirs
from quant_os.integrations.freqtrade.docker_ops import DockerOps
from quant_os.integrations.freqtrade.dry_run_adapter import FreqtradeDryRunAdapter


def build_operational_status() -> dict[str, object]:
    adapter = FreqtradeDryRunAdapter()
    docker = DockerOps()
    base_status = adapter.get_status()
    container = docker.get_container_status()
    log_json = Path("reports/freqtrade/logs/latest_logs.json")
    status = {
        "generated_at": datetime.now(UTC).isoformat(),
        "dry_run_only": True,
        "live_trading_enabled": False,
        "docker_available": docker.docker_available(),
        "compose_available": docker.compose_available(),
        "container_status": container.status,
        "config_valid": base_status["safety_guard_passed"],
        "strategy_exported": base_status["strategy_exported"],
        "last_log_ingestion": str(log_json) if log_json.exists() else None,
        "next_manual_commands": [
            "make.cmd freqtrade-dry-run-start",
            "make.cmd freqtrade-dry-run-logs",
            "make.cmd freqtrade-reconcile",
        ],
    }
    return status


def write_operational_status_report() -> dict[str, object]:
    dirs = ensure_freqtrade_artifact_dirs()
    status = build_operational_status()
    json_path = dirs["status_dir"] / "latest_operational_status.json"
    md_path = dirs["status_dir"] / "latest_operational_status.md"
    json_path.write_text(json.dumps(status, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Freqtrade Operational Status",
        "",
        "Dry-run only. No live trading. No keys.",
        "",
        f"Docker available: {status['docker_available']}",
        f"Container status: {status['container_status']}",
        f"Config valid: {status['config_valid']}",
        f"Strategy exported: {status['strategy_exported']}",
        f"Last log ingestion: {status['last_log_ingestion']}",
        "",
        "Manual next commands:",
        *[f"- `{command}`" for command in status["next_manual_commands"]],
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return status
