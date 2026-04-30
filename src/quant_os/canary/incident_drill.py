from __future__ import annotations

from typing import Any

from quant_os.canary.policy import CANARY_ROOT, write_canary_report
from quant_os.canary.rollback import build_rollback_plan

DRILL_JSON = CANARY_ROOT / "latest_incident_drill.json"
DRILL_MD = CANARY_ROOT / "latest_incident_drill.md"


def build_incident_drill(write: bool = True) -> dict[str, Any]:
    scenarios = [
        "LIVE_DANGER_EVIDENCE_APPEARS",
        "CANARY_CONNECTIVITY_LOSS",
        "RECONCILIATION_FAILURE",
        "STOPLOSS_EVIDENCE_MISSING",
        "API_PERMISSION_SCOPE_TOO_BROAD",
        "STRATEGY_DIVERGENCE",
        "FUTURE_DAILY_LOSS_CAP_BREACH",
    ]
    payload = {
        "status": "PLANNING_ONLY",
        "dry_drill_only": True,
        "live_trading_enabled": False,
        "scenarios": [
            {
                "scenario": scenario,
                "first_action": "activate_or_confirm_kill_switch",
                "second_action": "stop_future_canary_lane_and_preserve_artifacts",
                "third_action": "write_incident_record_and_require_human_review",
            }
            for scenario in scenarios
        ],
        "live_promotion_status": "LIVE_BLOCKED",
        "next_commands": ["make.cmd canary-readiness", "make.cmd canary-report"],
    }
    if write:
        write_canary_report(DRILL_JSON, DRILL_MD, "Canary Incident Drill", payload)
        build_rollback_plan(write=True)
    return payload
