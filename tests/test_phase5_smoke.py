from __future__ import annotations

from quant_os.integrations.freqtrade.dry_run_adapter import FreqtradeDryRunAdapter
from quant_os.integrations.freqtrade.log_ingestion import ingest_freqtrade_logs
from quant_os.monitoring.divergence import check_dryrun_divergence
from quant_os.monitoring.dryrun_comparison import build_dryrun_comparison
from quant_os.monitoring.dryrun_history import append_history_record
from quant_os.monitoring.monitoring_report import generate_dryrun_monitoring_report
from quant_os.monitoring.promotion_readiness import check_promotion_readiness


def test_phase5_smoke_passes_without_docker(local_project, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _name: None)
    adapter = FreqtradeDryRunAdapter()
    adapter.generate_config()
    adapter.export_strategy()
    adapter.write_run_manifest()
    ingest_freqtrade_logs("")
    history = append_history_record()
    comparison = build_dryrun_comparison()
    divergence = check_dryrun_divergence()
    report = generate_dryrun_monitoring_report()
    promotion = check_promotion_readiness()
    assert history["records_count"] >= 1
    assert comparison["status"] in {"PASS", "WARN"}
    assert divergence["status"] in {"PASS", "WARN"}
    assert report["status"] in {"PASS", "WARN"}
    assert promotion["live_promotion_status"] == "TINY_LIVE_BLOCKED"
