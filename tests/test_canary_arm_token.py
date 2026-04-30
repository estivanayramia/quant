from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from quant_os.canary.arm_token import generate_arm_token, validate_arm_token
from quant_os.governance.two_step_approval import write_approval_rehearsal


def test_arm_token_generated(local_project):
    payload = generate_arm_token()
    assert payload["status"] == "PASS"
    assert payload["rehearsal_only"] is True
    assert payload["live_unlocked"] is False
    assert Path("reports/canary/latest_arm_token.json").exists()


def test_expired_arm_token_blocks_rehearsal(local_project):
    record = {
        "token_id": "arm_expired",
        "expires_at": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
        "rehearsal_only": True,
        "live_unlocked": False,
    }
    payload = validate_arm_token(record=record)
    assert payload["status"] == "FAIL"
    assert "ARM_TOKEN_EXPIRED" in payload["blockers"]


def test_approval_rehearsal_generated(local_project):
    payload = write_approval_rehearsal()
    assert payload["status"] == "FAIL"
    assert "TWO_STEP_APPROVAL_NOT_COMPLETE" in payload["blockers"]
    assert Path("reports/canary/latest_approval_rehearsal.json").exists()
