from __future__ import annotations

from typing import Any

from quant_os.canary.approvals import ApprovalRecord, evaluate_approval
from quant_os.canary.policy import CANARY_ROOT, write_canary_report

APPROVAL_REHEARSAL_JSON = CANARY_ROOT / "latest_approval_rehearsal.json"
APPROVAL_REHEARSAL_MD = CANARY_ROOT / "latest_approval_rehearsal.md"


def write_approval_rehearsal(
    approvals: list[ApprovalRecord] | None = None,
    write: bool = True,
) -> dict[str, Any]:
    approval = evaluate_approval(approvals)
    blockers = list(approval["blockers"])
    if not approval["approval_present"]:
        blockers.append("TWO_STEP_APPROVAL_NOT_COMPLETE")
    payload = {
        "status": "FAIL" if blockers else "PASS",
        "rehearsal_only": True,
        "dual_confirmation_required": True,
        "approval_status": approval["status"],
        "approval_present": approval["approval_present"],
        "blockers": sorted(set(blockers)),
        "warnings": ["Approval rehearsal cannot unlock live trading in Phase 12."],
        "live_unlocked": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "next_commands": ["make.cmd canary-preflight-rehearsal"],
    }
    if write:
        write_canary_report(
            APPROVAL_REHEARSAL_JSON,
            APPROVAL_REHEARSAL_MD,
            "Canary Two-Step Approval Rehearsal",
            payload,
        )
    return payload
