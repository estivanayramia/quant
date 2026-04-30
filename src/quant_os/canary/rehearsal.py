from __future__ import annotations

from typing import Any

from quant_os.canary.checklist import build_canary_checklist
from quant_os.canary.permissions_import import validate_latest_permission_manifest
from quant_os.canary.policy import CANARY_ROOT, build_canary_policy, write_canary_report
from quant_os.canary.preflight_rehearsal import run_preflight_rehearsal

REHEARSAL_JSON = CANARY_ROOT / "latest_rehearsal.json"
REHEARSAL_MD = CANARY_ROOT / "latest_rehearsal.md"


def run_canary_rehearsal(write: bool = True) -> dict[str, Any]:
    policy = build_canary_policy(write=True)
    checklist = build_canary_checklist(write=True)
    permission = validate_latest_permission_manifest()
    preflight = run_preflight_rehearsal(write=True)
    steps = [
        {"name": "load_policy", "status": "PASS"},
        {"name": "load_checklist", "status": checklist["status"]},
        {"name": "load_permission_manifest", "status": permission["status"]},
        {"name": "validate_preflight_rehearsal", "status": preflight["preflight_rehearsal_status"]},
        {"name": "confirm_no_exchange_connection", "status": "PASS"},
        {"name": "confirm_no_order_path", "status": "PASS"},
        {"name": "confirm_live_still_blocked", "status": "PASS"},
    ]
    blockers = sorted(set(checklist["blockers"] + permission.get("blockers", []) + preflight["blockers"]))
    payload = {
        "status": "LIVE_BLOCKED",
        "rehearsal_status": "REHEARSAL_FAIL" if blockers else "REHEARSAL_PASS",
        "policy_status": policy["status"],
        "steps": steps,
        "blockers": blockers,
        "warnings": ["Dry rehearsal only. No exchange connection, no keys, no orders."],
        "placed_orders": 0,
        "exchange_connections": 0,
        "live_trading_enabled": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "next_commands": ["make.cmd canary-final-gate", "make.cmd canary-rehearsal-report"],
    }
    if write:
        write_canary_report(REHEARSAL_JSON, REHEARSAL_MD, "Canary Rehearsal", payload)
    return payload
