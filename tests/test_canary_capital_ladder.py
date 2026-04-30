from __future__ import annotations

from pathlib import Path

from quant_os.canary.capital_ladder import build_capital_ladder


def test_canary_capital_ladder_report_generated(local_project):
    payload = build_capital_ladder()
    assert payload["current_stage"] == "stage_0"
    assert payload["live_promotion_status"] == "LIVE_BLOCKED"
    assert Path("reports/canary/latest_capital_ladder.json").exists()
