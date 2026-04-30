from __future__ import annotations

from typing import Any

from quant_os.canary.policy import CANARY_ROOT, write_canary_report

ROLLBACK_JSON = CANARY_ROOT / "latest_rollback_plan.json"
ROLLBACK_MD = CANARY_ROOT / "latest_rollback_plan.md"


def build_rollback_plan(write: bool = True) -> dict[str, Any]:
    payload = {
        "status": "PLANNING_ONLY",
        "live_trading_enabled": False,
        "rollback_steps": [
            "activate_kill_switch",
            "stop_future_canary_process",
            "cancel_future_open_orders_if_a_future_live_phase_exists",
            "quarantine_strategy",
            "preserve_logs_event_ledger_and_exchange_reports",
            "run_reconciliation",
            "write_incident_report",
            "require_human_review_before_any_restart",
        ],
        "automatic_restart_allowed": False,
        "telegram_control_allowed": False,
        "ai_control_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "next_commands": ["make.cmd canary-incident-drill", "make.cmd canary-report"],
    }
    if write:
        write_canary_report(ROLLBACK_JSON, ROLLBACK_MD, "Canary Rollback Plan", payload)
    return payload
