from __future__ import annotations

from typing import Any

from quant_os.canary.permissions_import import validate_latest_permission_manifest
from quant_os.canary.policy import CANARY_ROOT, write_canary_report
from quant_os.canary.rehearsal import run_canary_rehearsal
from quant_os.canary.stoploss_proof import build_stoploss_proof

FINAL_GATE_JSON = CANARY_ROOT / "latest_final_gate.json"
FINAL_GATE_MD = CANARY_ROOT / "latest_final_gate.md"
REHEARSAL_REPORT_JSON = CANARY_ROOT / "latest_rehearsal_report.json"
REHEARSAL_REPORT_MD = CANARY_ROOT / "latest_rehearsal_report.md"


def evaluate_final_gate(write: bool = True) -> dict[str, Any]:
    permission = validate_latest_permission_manifest()
    rehearsal = run_canary_rehearsal(write=True)
    stoploss = build_stoploss_proof(write=True)
    blockers = sorted(
        set(
            permission.get("blockers", [])
            + rehearsal.get("blockers", [])
            + stoploss.get("blockers", [])
            + ["PHASE_12_LIVE_EXECUTION_NOT_IMPLEMENTED"]
        )
    )
    rehearsal_ready = permission["status"] == "PASS" and rehearsal["rehearsal_status"] != "REHEARSAL_FAIL"
    payload = {
        "status": "LIVE_BLOCKED",
        "final_gate_status": "LIVE_BLOCKED",
        "rehearsal_ready": rehearsal_ready,
        "policy_ready": permission["status"] == "PASS",
        "future_canary_considerable": False,
        "live_blocked": True,
        "what_is_satisfied": _satisfied(permission, rehearsal),
        "what_is_missing": blockers,
        "future_only_conditions_remaining": [
            "real exchange permission verification without credentials in repo",
            "stoploss-on-exchange proof artifact",
            "human approval outside this rehearsal",
            "separate future implementation that still passes all guards",
        ],
        "why_live_remains_blocked": [
            "Phase 12 is rehearsal-only.",
            "No exchange adapter can place live orders.",
            "Final gate is hard-coded to keep live blocked.",
        ],
        "blockers": blockers,
        "warnings": ["Final gate summarizes rehearsal evidence only."],
        "live_promotion_status": "LIVE_BLOCKED",
        "next_commands": ["make.cmd canary-rehearsal-report", "make.cmd guard-live"],
    }
    if write:
        write_canary_report(FINAL_GATE_JSON, FINAL_GATE_MD, "Canary Final Gate", payload)
        write_canary_report(
            REHEARSAL_REPORT_JSON,
            REHEARSAL_REPORT_MD,
            "Canary Rehearsal Report",
            payload,
        )
    return payload


def write_rehearsal_report() -> dict[str, Any]:
    return evaluate_final_gate(write=True)


def _satisfied(permission: dict[str, Any], rehearsal: dict[str, Any]) -> list[str]:
    satisfied = ["live_flags_remain_false", "no_exchange_connection", "no_order_path"]
    if permission["status"] == "PASS":
        satisfied.append("permission_manifest_imported_and_valid")
    if rehearsal["rehearsal_status"] != "REHEARSAL_FAIL":
        satisfied.append("rehearsal_sequence_completed_without_blockers")
    return satisfied
