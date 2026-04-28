from __future__ import annotations

from quant_os.autonomy.supervisor import Supervisor
from quant_os.integrations.freqtrade.artifact_scanner import scan_freqtrade_artifacts
from quant_os.integrations.freqtrade.trade_normalizer import (
    ingest_trade_artifacts,
    normalize_trade_artifacts,
)
from quant_os.integrations.freqtrade.trade_reconciliation import reconcile_freqtrade_trades
from quant_os.integrations.freqtrade.trade_reporting import write_freqtrade_trade_report


def test_phase6_smoke_passes_without_docker_or_real_artifacts(local_project, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _name: None)
    scan = scan_freqtrade_artifacts()
    ingestion = ingest_trade_artifacts()
    normalized = normalize_trade_artifacts()
    reconciliation = reconcile_freqtrade_trades()
    report = write_freqtrade_trade_report()
    state = Supervisor().run_once()
    assert scan["status"] in {"PASS", "UNAVAILABLE"}
    assert ingestion["status"] in {"PASS", "WARN", "UNAVAILABLE"}
    assert normalized["status"] in {"PASS", "WARN", "UNAVAILABLE"}
    assert reconciliation["status"] in {"PASS", "WARN", "UNAVAILABLE"}
    assert report["trade_reconciliation_status"] in {"PASS", "WARN", "UNAVAILABLE"}
    assert "freqtrade_trade_artifacts" in state.freqtrade_trade_artifacts_summary
