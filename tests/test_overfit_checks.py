from __future__ import annotations

from pathlib import Path

from quant_os.research.overfit_checks import run_overfit_checks


def test_overfit_checks_flag_low_trade_count_and_placebo_weakness(local_project) -> None:
    payload = run_overfit_checks()
    assert any("LOW_TRADE_COUNT" in warning for warning in payload["warnings"])
    assert payload["live_promotion_status"] == "TINY_LIVE_BLOCKED"
    assert Path("reports/strategy/overfit/latest_overfit_check.json").exists()
