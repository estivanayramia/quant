from __future__ import annotations

from quant_os.live_canary.live_report import write_live_canary_report_bundle


def test_live_canary_report_generated(local_project):
    payload = write_live_canary_report_bundle()
    assert payload["live_promotion_status"] == "LIVE_BLOCKED"
    assert payload["real_order_attempted"] is False

