from __future__ import annotations

from typing import Any

from quant_os.canary.arm_token import validate_arm_token
from quant_os.canary.final_gate import evaluate_final_gate
from quant_os.canary.permissions_import import validate_latest_permission_manifest
from quant_os.canary.preflight_rehearsal import run_preflight_rehearsal
from quant_os.canary.stoploss_proof import build_stoploss_proof
from quant_os.governance.two_step_approval import write_approval_rehearsal


def canary_rehearsal_status() -> dict[str, Any]:
    permission = validate_latest_permission_manifest()
    arm = validate_arm_token()
    approval = write_approval_rehearsal(write=True)
    stoploss = build_stoploss_proof(write=True)
    preflight = run_preflight_rehearsal(write=True)
    final_gate = evaluate_final_gate(write=True)
    blockers = sorted(
        set(
            permission.get("blockers", [])
            + arm.get("blockers", [])
            + approval.get("blockers", [])
            + stoploss.get("blockers", [])
            + preflight.get("blockers", [])
            + final_gate.get("blockers", [])
        )
    )
    return {
        "permission_manifest_status": permission["status"],
        "arming_status": arm["status"],
        "approval_rehearsal_status": approval["status"],
        "stoploss_proof_status": stoploss["status"],
        "preflight_rehearsal_status": preflight["preflight_rehearsal_status"],
        "final_gate_status": final_gate["final_gate_status"],
        "blockers": blockers,
        "live_promotion_status": "LIVE_BLOCKED",
        "latest_report_path": "reports/canary/latest_rehearsal_report.md",
    }
