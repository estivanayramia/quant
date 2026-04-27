from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import yaml

from quant_os.adapters.event_store_jsonl import JsonlEventStore
from quant_os.adapters.market_data_parquet import LocalParquetMarketData
from quant_os.data.demo_data import seed_demo_data
from quant_os.data.quality import validate_ohlcv
from quant_os.projections.rebuild import rebuild_read_models
from quant_os.security.config_guard import config_guard
from quant_os.security.live_trading_guard import live_trading_guard
from quant_os.security.secrets_guard import secrets_guard
from quant_os.watchdog.process_lock import lock_exists


@dataclass
class HealthCheck:
    name: str
    passed: bool
    critical: bool = True
    details: dict[str, object] = field(default_factory=dict)


@dataclass
class HealthReport:
    status: str
    generated_at: str
    checks: list[HealthCheck]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks if check.critical)

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "generated_at": self.generated_at,
            "checks": [asdict(check) for check in self.checks],
        }


def run_watchdog(
    event_store: JsonlEventStore | None = None,
    output_dir: str | Path = "reports/watchdog",
) -> HealthReport:
    event_store = event_store or JsonlEventStore()
    checks: list[HealthCheck] = []
    checks.append(HealthCheck("repo_path_valid", Path("pyproject.toml").exists()))
    checks.append(_guard_check("config_guard", config_guard()))
    checks.append(_guard_check("live_trading_guard", live_trading_guard()))
    checks.append(_guard_check("secrets_guard", secrets_guard()))
    checks.append(_configs_load())
    checks.append(_event_ledger_writable(event_store))
    checks.append(_read_model_rebuildable(event_store))
    checks.append(
        HealthCheck(
            "latest_report_exists", Path("reports/daily_report.md").exists(), critical=False
        )
    )
    checks.append(HealthCheck("kill_switch_readable", Path("configs/risk_limits.yaml").exists()))
    checks.append(
        HealthCheck("strategy_registry_readable", Path("configs/strategies.yaml").exists())
    )
    checks.append(_data_files_and_quality(event_store))
    checks.append(HealthCheck("no_duplicate_daemon_lock", not lock_exists(), critical=False))
    checks.append(_disk_space_check())
    checks.append(_clock_sanity_check())
    report = HealthReport(
        status="passed" if all(check.passed for check in checks if check.critical) else "failed",
        generated_at=datetime.now(UTC).isoformat(),
        checks=checks,
    )
    _write_report(report, output_dir)
    return report


def _guard_check(name: str, result) -> HealthCheck:
    return HealthCheck(name, result.passed, details={"reasons": result.reasons, **result.details})


def _configs_load() -> HealthCheck:
    try:
        for path in Path("configs").glob("*.yaml"):
            yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - exercised through failure reports
        return HealthCheck("config_files_load", False, details={"error": str(exc)})
    return HealthCheck("config_files_load", True)


def _event_ledger_writable(event_store: JsonlEventStore) -> HealthCheck:
    try:
        event_store.path.parent.mkdir(parents=True, exist_ok=True)
        with event_store.path.open("a", encoding="utf-8"):
            pass
    except OSError as exc:
        return HealthCheck("event_ledger_writable", False, details={"error": str(exc)})
    return HealthCheck("event_ledger_writable", True)


def _read_model_rebuildable(event_store: JsonlEventStore) -> HealthCheck:
    try:
        rebuild_read_models(event_store, "data/read_models/watchdog.duckdb")
    except Exception as exc:
        return HealthCheck("read_model_rebuildable", False, details={"error": str(exc)})
    return HealthCheck("read_model_rebuildable", True)


def _data_files_and_quality(event_store: JsonlEventStore) -> HealthCheck:
    try:
        if not list(Path("data/demo").glob("*.parquet")):
            seed_demo_data(event_store=event_store)
        frame = LocalParquetMarketData().load()
        summary = validate_ohlcv(frame)
    except Exception as exc:
        return HealthCheck(
            "data_files_exist_and_quality_passes", False, details={"error": str(exc)}
        )
    return HealthCheck("data_files_exist_and_quality_passes", True, details=summary)


def _disk_space_check() -> HealthCheck:
    try:
        usage = shutil.disk_usage(Path.cwd())
        free_gb = usage.free / (1024**3)
        return HealthCheck(
            "disk_space_sane", free_gb > 0.5, critical=False, details={"free_gb": round(free_gb, 2)}
        )
    except OSError as exc:
        return HealthCheck("disk_space_sane", True, critical=False, details={"warning": str(exc)})


def _clock_sanity_check() -> HealthCheck:
    now = datetime.now(UTC)
    return HealthCheck(
        "clock_sanity", now.year >= 2025, critical=False, details={"utc_now": now.isoformat()}
    )


def _write_report(report: HealthReport, output_dir: str | Path) -> None:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    payload = report.to_dict()
    (root / "latest_health.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    lines = ["# Watchdog Health", "", f"Status: {report.status}", ""]
    for check in report.checks:
        marker = "PASS" if check.passed else "FAIL"
        lines.append(f"- {marker} {check.name} critical={check.critical} details={check.details}")
    (root / "latest_health.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
