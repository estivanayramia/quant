from __future__ import annotations

from pathlib import Path

from quant_os.integrations.freqtrade.dry_run_adapter import FreqtradeDryRunAdapter
from quant_os.monitoring.dryrun_history import append_history_record, build_history_record


def _prepare() -> None:
    adapter = FreqtradeDryRunAdapter()
    adapter.generate_config()
    adapter.export_strategy()
    adapter.write_run_manifest()


def test_history_record_can_be_created(local_project):
    _prepare()
    record = build_history_record()
    assert record["dry_run"] is True
    assert record["live_trading_enabled"] is False
    assert record["config_hash"]


def test_history_handles_missing_freqtrade_logs_gracefully(local_project):
    _prepare()
    latest = append_history_record()
    assert latest["records_count"] == 1
    assert Path("reports/dryrun/latest_history.json").exists()
    assert latest["latest_record"]["freqtrade_log_summary"]["line_count"] == 0
