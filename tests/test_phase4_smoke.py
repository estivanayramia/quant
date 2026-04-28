from __future__ import annotations

from quant_os.autonomy.supervisor import Supervisor
from quant_os.integrations.freqtrade.log_ingestion import ingest_freqtrade_logs
from quant_os.integrations.freqtrade.operational_status import write_operational_status_report
from quant_os.integrations.freqtrade.reconciliation import reconcile_freqtrade
from quant_os.integrations.freqtrade.runner import FreqtradeRunner


def test_phase4_smoke_without_docker(local_project, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _name: None)
    runner = FreqtradeRunner()
    runner.prepare()
    ingest_freqtrade_logs("")
    reconciliation = reconcile_freqtrade()
    status = write_operational_status_report()
    assert reconciliation["status"] in {"PASS", "WARN"}
    assert status["docker_available"] is False


def test_autonomous_report_includes_freqtrade_operational_section(local_project, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _name: None)
    state = Supervisor().run_once()
    freqtrade = state.freqtrade_summary["freqtrade"]
    assert freqtrade["autonomous_start_allowed"] is False
    assert "container_status" in freqtrade
    assert "reconciliation_status" in freqtrade
