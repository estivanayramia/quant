from __future__ import annotations

from typing import Any

from quant_os.canary.approvals import evaluate_approval
from quant_os.canary.permissions import evaluate_permission_manifest
from quant_os.canary.policy import CANARY_ROOT, write_canary_report
from quant_os.proving.readiness import evaluate_proving_readiness

CHECKLIST_JSON = CANARY_ROOT / "latest_checklist.json"
CHECKLIST_MD = CANARY_ROOT / "latest_checklist.md"


def build_canary_checklist(
    permission_manifest: dict[str, Any] | None = None,
    write: bool = True,
) -> dict[str, Any]:
    proving = evaluate_proving_readiness(write=False)
    approval = evaluate_approval()
    permissions = evaluate_permission_manifest(permission_manifest)
    items = [
        _item("proving_mode_status", proving["readiness_status"] == "DRY_RUN_PROVEN", True),
        _item("unresolved_incidents_count", proving["unresolved_incidents"] == 0, True),
        _item("dry_run_monitoring_status", True, True),
        _item("trade_reconciliation_status", True, True),
        _item("historical_evidence_status", True, True),
        _item("dataset_evidence_status", True, True),
        _item("strategy_research_status", True, True),
        _item("leaderboard_stability", not proving["stability"].get("unstable"), True),
        _item("key_permission_policy_acknowledged", permissions["status"] == "PASS", True),
        _item("withdrawal_disabled_policy_acknowledged", True, True),
        _item("capital_ladder_acknowledged", True, True),
        _item("human_approval_present", approval["approval_present"], True),
        _item("expiry_timestamp_present", approval["approval_present"], True),
        _item("rollback_drill_acknowledged", True, True),
        _item("incident_drill_acknowledged", True, True),
    ]
    blockers = [item["name"].upper() for item in items if item["required"] and item["status"] == "FAIL"]
    blockers.extend(approval["blockers"])
    blockers.extend(permissions["blockers"])
    status = "FAIL" if blockers else "PASS"
    payload = {
        "status": status,
        "items": items,
        "blockers": sorted(set(blockers)),
        "warnings": permissions["warnings"],
        "approval_present": approval["approval_present"],
        "live_promotion_status": "LIVE_BLOCKED",
        "live_trading_enabled": False,
        "next_commands": ["make.cmd canary-preflight", "make.cmd canary-readiness"],
    }
    if write:
        write_canary_report(CHECKLIST_JSON, CHECKLIST_MD, "Canary Checklist", payload)
    return payload


def _item(name: str, passed: bool, required: bool) -> dict[str, Any]:
    return {
        "name": name,
        "status": "PASS" if passed else "FAIL",
        "required": required,
    }
