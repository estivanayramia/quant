from __future__ import annotations

from pathlib import Path

from quant_os.integrations.freqtrade.operational_status import write_operational_status_report


def test_operational_status_report_generated(local_project):
    payload = write_operational_status_report()
    assert payload["dry_run_only"] is True
    assert Path("reports/freqtrade/status/latest_operational_status.json").exists()
    assert Path("reports/freqtrade/status/latest_operational_status.md").exists()
