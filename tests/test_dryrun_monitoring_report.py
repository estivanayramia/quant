from __future__ import annotations

from pathlib import Path

from quant_os.autonomy.supervisor import Supervisor
from quant_os.integrations.freqtrade.dry_run_adapter import FreqtradeDryRunAdapter
from quant_os.integrations.freqtrade.log_ingestion import ingest_freqtrade_logs
from quant_os.monitoring.monitoring_report import generate_dryrun_monitoring_report


def _prepare() -> None:
    adapter = FreqtradeDryRunAdapter()
    adapter.generate_config()
    adapter.export_strategy()
    adapter.write_run_manifest()
    ingest_freqtrade_logs("")


def test_monitoring_report_generated(local_project):
    _prepare()
    payload = generate_dryrun_monitoring_report()
    assert payload["live_promotion_status"] == "TINY_LIVE_BLOCKED"
    assert Path("reports/dryrun/latest_monitoring_report.md").exists()
    assert Path("reports/dryrun/latest_monitoring_report.json").exists()


def test_autonomous_report_includes_dryrun_monitoring(local_project, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _name: None)
    state = Supervisor().run_once()
    summary = state.dryrun_monitoring_summary["dryrun_monitoring"]
    assert summary["autonomous_start_allowed"] is False
    assert summary["live_promotion_status"] == "TINY_LIVE_BLOCKED"
