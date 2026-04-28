from __future__ import annotations

from pathlib import Path

from quant_os.research.research_report import write_strategy_research_report


def test_strategy_research_report_generated(local_project) -> None:
    payload = write_strategy_research_report()
    assert payload["live_promotion_status"] == "TINY_LIVE_BLOCKED"
    assert payload["strategy_list"]
    assert Path("reports/strategy/latest_research_report.md").exists()
