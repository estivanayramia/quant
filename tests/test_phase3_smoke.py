from __future__ import annotations

from pathlib import Path

from quant_os.autonomy.supervisor import Supervisor
from quant_os.integrations.freqtrade.dry_run_adapter import FreqtradeDryRunAdapter
from quant_os.ops.freqtrade_reporting import write_freqtrade_status_report


def test_phase3_smoke_components_pass(local_project):
    adapter = FreqtradeDryRunAdapter()
    adapter.generate_config()
    adapter.export_strategy()
    assert adapter.validate_config().passed
    adapter.write_run_manifest()
    status = write_freqtrade_status_report()
    assert status["safety_guard_passed"] is True
    assert Path("reports/freqtrade/latest_status.json").exists()
    assert Path("reports/freqtrade/latest_status.md").exists()


def test_autonomous_report_includes_freqtrade_status(local_project):
    state = Supervisor().run_once()
    assert state.status.value == "completed"
    assert state.freqtrade_summary["freqtrade"]["dry_run_config_present"] is True
    assert state.freqtrade_summary["freqtrade"]["safety_guard_passed"] is True
