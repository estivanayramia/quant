from __future__ import annotations

from typing import Any

from quant_os.canary.report import write_canary_report_bundle


def canary_planning_status() -> dict[str, Any]:
    payload = write_canary_report_bundle()
    return {
        "policy_status": payload["policy_status"],
        "checklist_status": payload["checklist_status"],
        "preflight_status": payload["preflight_status"],
        "readiness_status": payload["readiness_status"],
        "blockers": payload["blockers"],
        "approval_present": payload["approval_present"],
        "current_capital_stage": payload["current_capital_stage"],
        "live_promotion_status": "LIVE_BLOCKED",
        "latest_report_path": payload["latest_report_path"],
    }
