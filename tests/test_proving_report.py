from __future__ import annotations

from pathlib import Path

from quant_os.proving.proving_report import write_proving_report
from quant_os.proving.run_history import append_proving_record
from quant_os.proving.run_record import ProvingRunRecord


def test_proving_report_is_generated(local_project) -> None:
    append_proving_record(
        ProvingRunRecord(
            run_id="run_report",
            timestamp="2024-01-01T00:00:00+00:00",
            run_status="completed",
            autonomous_status="completed",
            top_strategy_id="baseline",
        )
    )
    report = write_proving_report()
    assert report["live_promotion_status"] == "LIVE_BLOCKED"
    assert Path("reports/proving/latest_proving_report.md").exists()
