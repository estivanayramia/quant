from __future__ import annotations

from quant_os.live_canary.live_status import live_canary_status, stop_live_canary


def test_live_status_report_generated(local_project):
    payload = live_canary_status()
    assert payload["live_fire_enabled"] is False
    assert payload["live_promotion_status"] == "LIVE_BLOCKED"


def test_live_stop_activates_kill_switch(local_project, tmp_path):
    payload = stop_live_canary(kill_switch_path=tmp_path / "kill.json")
    assert payload["status"] == "STOPPED"
    assert payload["kill_switch_status"] == "ACTIVE"

