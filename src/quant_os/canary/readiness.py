from __future__ import annotations

from typing import Any

from quant_os.canary.approvals import ApprovalRecord
from quant_os.canary.policy import CANARY_ROOT, write_canary_report
from quant_os.canary.preflight import evaluate_canary_preflight

READINESS_JSON = CANARY_ROOT / "latest_readiness.json"
READINESS_MD = CANARY_ROOT / "latest_readiness.md"


def evaluate_canary_readiness(
    approvals: list[ApprovalRecord] | None = None,
    permission_manifest: dict[str, Any] | None = None,
    write: bool = True,
) -> dict[str, Any]:
    # If tests pass explicit approvals, evaluate them through the checklist path by writing nothing.
    from quant_os.canary.approvals import evaluate_approval

    approval = evaluate_approval(approvals) if approvals is not None else evaluate_approval()
    preflight = evaluate_canary_preflight(permission_manifest=permission_manifest, write=False)
    blockers = sorted(set(preflight["blockers"] + approval["blockers"] + ["PHASE_11_LIVE_EXECUTION_NOT_IMPLEMENTED"]))
    if not approval["approval_present"]:
        planning_status = "NOT_APPROVED"
    elif any("PERMISSION" in blocker or "CREDENTIAL" in blocker for blocker in blockers):
        planning_status = "BLOCKED_BY_PERMISSIONS"
    elif len(blockers) > 1:
        planning_status = "BLOCKED_BY_EVIDENCE"
    else:
        planning_status = "PLANNING_ONLY"
    payload = {
        "status": "LIVE_BLOCKED",
        "readiness_status": "LIVE_BLOCKED",
        "planning_status": planning_status,
        "preflight_status": preflight["preflight_status"],
        "approval_present": approval["approval_present"],
        "blockers": blockers,
        "warnings": preflight["warnings"],
        "what_is_satisfied": _satisfied(preflight, approval),
        "what_is_missing": blockers,
        "why_live_is_still_blocked": [
            "Phase 11 creates policy and gates only.",
            "No live execution adapter is enabled.",
            "Human approval cannot unlock live by itself.",
            "Future stoploss-on-exchange and key-scope verification are not proven.",
        ],
        "future_evidence_needed": [
            "multi-cycle DRY_RUN_PROVEN proving status",
            "zero unresolved incidents",
            "trade-level reconciliation evidence",
            "restricted API permission manifest",
            "stoploss-on-exchange proof in a future dry-run/paper gate",
            "explicit human review outside this scaffold",
        ],
        "live_promotion_status": "LIVE_BLOCKED",
        "live_allowed": False,
        "next_commands": ["make.cmd canary-report", "make.cmd proving-readiness"],
    }
    if write:
        write_canary_report(READINESS_JSON, READINESS_MD, "Canary Readiness", payload)
    return payload


def _satisfied(preflight: dict[str, Any], approval: dict[str, Any]) -> list[str]:
    satisfied = ["live_trading_guard_passed"] if not preflight.get("live_trading_enabled") else []
    if approval["approval_present"]:
        satisfied.append("human_approval_present")
    return satisfied
