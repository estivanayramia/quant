from __future__ import annotations

from pathlib import Path

from quant_os.watchdog.health_checks import run_watchdog


def test_watchdog_health_report_generated(local_project):
    report = run_watchdog()
    assert report.passed
    assert Path("reports/watchdog/latest_health.json").exists()
    assert Path("reports/watchdog/latest_health.md").exists()
