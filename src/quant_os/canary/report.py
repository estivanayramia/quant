from __future__ import annotations

from typing import Any

from quant_os.canary.capital_ladder import build_capital_ladder
from quant_os.canary.checklist import build_canary_checklist
from quant_os.canary.incident_drill import build_incident_drill
from quant_os.canary.policy import CANARY_ROOT, build_canary_policy, write_canary_report
from quant_os.canary.preflight import evaluate_canary_preflight
from quant_os.canary.readiness import evaluate_canary_readiness
from quant_os.canary.rollback import build_rollback_plan

REPORT_JSON = CANARY_ROOT / "latest_report.json"
REPORT_MD = CANARY_ROOT / "latest_report.md"


def write_canary_report_bundle(write: bool = True) -> dict[str, Any]:
    policy = build_canary_policy(write=True)
    checklist = build_canary_checklist(write=True)
    preflight = evaluate_canary_preflight(write=True)
    ladder = build_capital_ladder(write=True)
    drill = build_incident_drill(write=True)
    rollback = build_rollback_plan(write=True)
    readiness = evaluate_canary_readiness(write=True)
    payload = {
        "status": "LIVE_BLOCKED",
        "policy_status": policy["status"],
        "checklist_status": checklist["status"],
        "preflight_status": preflight["preflight_status"],
        "readiness_status": readiness["readiness_status"],
        "current_capital_stage": ladder["current_stage_label"],
        "incident_drill_status": drill["status"],
        "rollback_plan_status": rollback["status"],
        "approval_present": readiness["approval_present"],
        "blockers": readiness["blockers"],
        "warnings": readiness["warnings"],
        "live_trading_enabled": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "latest_report_path": str(REPORT_MD),
        "next_commands": [
            "make.cmd canary-preflight",
            "make.cmd canary-readiness",
            "make.cmd proving-run-once",
        ],
    }
    if write:
        write_canary_report(REPORT_JSON, REPORT_MD, "Canary Planning Report", payload)
    return payload
