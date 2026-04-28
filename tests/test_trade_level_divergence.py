from __future__ import annotations

from quant_os.monitoring.trade_level_divergence import check_trade_level_divergence
from quant_os.monitoring.trade_level_readiness import trade_level_readiness_status


def test_trade_level_divergence_reports_unavailable_without_artifacts(local_project):
    payload = check_trade_level_divergence()
    assert payload["status"] in {"UNAVAILABLE", "WARN"}


def test_trade_level_readiness_blocks_live(local_project):
    payload = trade_level_readiness_status()
    assert payload["live_promotion_status"] == "TINY_LIVE_BLOCKED"
    assert payload["live_eligible"] is False
