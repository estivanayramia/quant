from __future__ import annotations

from quant_os.autonomy.supervisor import Supervisor
from quant_os.live_canary.capabilities import inspect_exchange_capabilities
from quant_os.live_canary.live_preflight import prepare_live_canary, run_live_preflight
from quant_os.live_canary.live_reconcile import reconcile_live_canary
from quant_os.live_canary.live_report import write_live_canary_report_bundle
from quant_os.live_canary.live_status import live_canary_status, stop_live_canary


def test_phase14_smoke_passes_fake_only_without_live_fire(local_project):
    assert inspect_exchange_capabilities()["status"] == "FAKE_ONLY"
    assert prepare_live_canary()["status"] == "BLOCKED"
    assert run_live_preflight()["status"] == "LIVE_BLOCKED"
    assert live_canary_status()["live_fire_enabled"] is False
    assert reconcile_live_canary()["status"] == "PASS"
    assert stop_live_canary()["status"] == "STOPPED"
    assert write_live_canary_report_bundle()["live_promotion_status"] == "LIVE_BLOCKED"
    state = Supervisor().run_once()
    live = state.live_canary_summary["live_canary"]
    assert live["adapter_mode"] == "fake"
    assert live["live_fire_enabled"] is False
