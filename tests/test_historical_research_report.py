from __future__ import annotations

from pathlib import Path

from quant_os.data.historical_import import import_historical_csv
from quant_os.research.historical_research_report import write_historical_research_report

FIXTURES = Path(__file__).parent / "fixtures" / "historical"


def test_historical_research_report_generated(local_project) -> None:
    import_historical_csv(FIXTURES / "sample_ohlcv_standard.csv")
    report = write_historical_research_report()
    assert report["live_promotion_status"] == "LIVE_BLOCKED"
    assert Path("reports/historical/evidence/latest_historical_research_report.md").exists()
