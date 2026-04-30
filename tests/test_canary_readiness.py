from __future__ import annotations

from datetime import UTC, datetime, timedelta

from quant_os.canary.approvals import ApprovalRecord
from quant_os.canary.readiness import evaluate_canary_readiness


def test_missing_approval_blocks_readiness(local_project):
    payload = evaluate_canary_readiness(approvals=[])
    assert payload["readiness_status"] == "LIVE_BLOCKED"
    assert "HUMAN_APPROVAL_MISSING" in payload["blockers"]


def test_revoked_approval_blocks_readiness(local_project):
    approval = ApprovalRecord(
        approval_id="a1",
        rationale="future canary review",
        expiry=(datetime.now(UTC) + timedelta(days=1)).isoformat(),
        acknowledged_risks=["loss", "outage"],
        revoked=True,
    )
    payload = evaluate_canary_readiness(approvals=[approval])
    assert "HUMAN_APPROVAL_REVOKED" in payload["blockers"]
    assert payload["readiness_status"] == "LIVE_BLOCKED"


def test_expired_approval_blocks_readiness(local_project):
    approval = ApprovalRecord(
        approval_id="a2",
        rationale="future canary review",
        expiry=(datetime.now(UTC) - timedelta(days=1)).isoformat(),
        acknowledged_risks=["loss", "outage"],
    )
    payload = evaluate_canary_readiness(approvals=[approval])
    assert "HUMAN_APPROVAL_EXPIRED" in payload["blockers"]
    assert payload["readiness_status"] == "LIVE_BLOCKED"
