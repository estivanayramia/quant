from __future__ import annotations

from quant_os.autonomy.supervisor import Supervisor
from quant_os.canary.capital_ladder import build_capital_ladder
from quant_os.canary.checklist import build_canary_checklist
from quant_os.canary.incident_drill import build_incident_drill
from quant_os.canary.policy import build_canary_policy
from quant_os.canary.preflight import evaluate_canary_preflight
from quant_os.canary.readiness import evaluate_canary_readiness
from quant_os.canary.report import write_canary_report_bundle


def test_phase11_smoke_passes(local_project):
    assert build_canary_policy()["live_promotion_status"] == "LIVE_BLOCKED"
    assert build_canary_checklist()["status"] == "FAIL"
    assert evaluate_canary_preflight()["status"] == "LIVE_BLOCKED"
    assert build_incident_drill()["live_promotion_status"] == "LIVE_BLOCKED"
    assert build_capital_ladder()["current_stage"] == "stage_0"
    assert evaluate_canary_readiness()["readiness_status"] == "LIVE_BLOCKED"
    assert write_canary_report_bundle()["status"] == "LIVE_BLOCKED"
    state = Supervisor().run_once()
    assert state.canary_planning_summary["live_promotion_status"] == "LIVE_BLOCKED"
