from __future__ import annotations

from typing import Any

from quant_os.canary.arm_token import validate_arm_token
from quant_os.canary.incident_drill import build_incident_drill
from quant_os.canary.permissions_import import validate_latest_permission_manifest
from quant_os.canary.policy import CANARY_ROOT, write_canary_report
from quant_os.canary.rollback import build_rollback_plan
from quant_os.canary.stoploss_proof import build_stoploss_proof
from quant_os.governance.two_step_approval import write_approval_rehearsal
from quant_os.proving.readiness import evaluate_proving_readiness
from quant_os.security.live_canary_guard import live_canary_guard
from quant_os.security.live_trading_guard import live_trading_guard

PREFLIGHT_REHEARSAL_JSON = CANARY_ROOT / "latest_preflight_rehearsal.json"
PREFLIGHT_REHEARSAL_MD = CANARY_ROOT / "latest_preflight_rehearsal.md"


def run_preflight_rehearsal(write: bool = True) -> dict[str, Any]:
    permission = validate_latest_permission_manifest()
    arm = validate_arm_token()
    approval = write_approval_rehearsal(write=True)
    stoploss = build_stoploss_proof(write=True)
    proving = evaluate_proving_readiness(write=False)
    drill = build_incident_drill(write=True)
    rollback = build_rollback_plan(write=True)
    live_guard = live_trading_guard()
    canary_guard = live_canary_guard()
    checks = {
        "proving_status": _check_status(proving["readiness_status"] == "DRY_RUN_PROVEN"),
        "unresolved_incidents": _check_status(proving["unresolved_incidents"] == 0),
        "dry_run_monitoring": "WARN",
        "trade_reconciliation": "WARN",
        "historical_evidence": "WARN",
        "strategy_research": "WARN",
        "approval_present": _check_status(approval["approval_present"]),
        "permission_manifest_valid": _check_status(permission["status"] == "PASS"),
        "arming_token_valid": _check_status(arm["status"] == "PASS"),
        "stoploss_proof_status": "FAIL" if stoploss["blockers"] else "PASS",
        "rollback_plan_present": _check_status(bool(rollback)),
        "incident_drill_present": _check_status(bool(drill)),
        "capital_ladder_acknowledged": "PASS",
        "live_flags_false": _check_status(live_guard.passed and canary_guard.passed),
    }
    blockers = []
    blockers.extend(permission.get("blockers", []))
    blockers.extend(arm.get("blockers", []))
    blockers.extend(approval.get("blockers", []))
    blockers.extend(stoploss.get("blockers", []))
    blockers.extend(proving.get("blockers", []))
    blockers.extend(live_guard.reasons)
    blockers.extend(canary_guard.reasons)
    rehearsal_status = "REHEARSAL_FAIL" if blockers else "REHEARSAL_PASS"
    payload = {
        "status": "LIVE_BLOCKED",
        "preflight_rehearsal_status": rehearsal_status,
        "checks": checks,
        "blockers": sorted(set(blockers)),
        "warnings": [
            "This is a rehearsal only; no exchange connection or order path exists.",
        ],
        "no_exchange_connection": True,
        "no_order_path": True,
        "live_promotion_status": "LIVE_BLOCKED",
        "next_commands": ["make.cmd canary-rehearsal", "make.cmd canary-final-gate"],
    }
    if write:
        write_canary_report(
            PREFLIGHT_REHEARSAL_JSON,
            PREFLIGHT_REHEARSAL_MD,
            "Canary Preflight Rehearsal",
            payload,
        )
    return payload


def _check_status(passed: bool) -> str:
    return "PASS" if passed else "FAIL"
