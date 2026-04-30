from __future__ import annotations

from pathlib import Path

from quant_os.canary.policy import build_canary_policy


def test_canary_policy_report_generated(local_project):
    payload = build_canary_policy()
    assert payload["status"] == "PLANNING_ONLY"
    assert payload["live_promotion_status"] == "LIVE_BLOCKED"
    assert Path("reports/canary/latest_policy.json").exists()
