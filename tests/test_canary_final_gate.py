from __future__ import annotations

from pathlib import Path

from quant_os.canary.arm_token import generate_arm_token
from quant_os.canary.final_gate import evaluate_final_gate
from quant_os.canary.permissions_import import import_permission_manifest

FIXTURE = Path(__file__).parent / "fixtures" / "canary" / "permission_manifest_safe.yaml"


def test_missing_approval_blocks_final_gate(local_project):
    import_permission_manifest(FIXTURE)
    generate_arm_token()
    payload = evaluate_final_gate()
    assert payload["status"] == "LIVE_BLOCKED"
    assert "HUMAN_APPROVAL_MISSING" in payload["blockers"]


def test_final_gate_remains_live_blocked(local_project):
    payload = evaluate_final_gate()
    assert payload["final_gate_status"] == "LIVE_BLOCKED"
    assert payload["live_blocked"] is True
    assert "PHASE_12_LIVE_EXECUTION_NOT_IMPLEMENTED" in payload["blockers"]
