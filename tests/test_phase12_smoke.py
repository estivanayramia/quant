from __future__ import annotations

from pathlib import Path

from quant_os.autonomy.supervisor import Supervisor
from quant_os.canary.arm_token import generate_arm_token
from quant_os.canary.final_gate import evaluate_final_gate, write_rehearsal_report
from quant_os.canary.permissions_import import import_permission_manifest
from quant_os.canary.preflight_rehearsal import run_preflight_rehearsal
from quant_os.canary.rehearsal import run_canary_rehearsal
from quant_os.canary.stoploss_proof import build_stoploss_proof

FIXTURE = Path(__file__).parent / "fixtures" / "canary" / "permission_manifest_safe.yaml"


def test_phase12_smoke_passes(local_project):
    assert import_permission_manifest(FIXTURE)["status"] == "PASS"
    assert generate_arm_token()["status"] == "PASS"
    assert run_preflight_rehearsal()["status"] == "LIVE_BLOCKED"
    assert build_stoploss_proof()["status"] == "FUTURE_PROOF_REQUIRED"
    assert run_canary_rehearsal()["status"] == "LIVE_BLOCKED"
    assert evaluate_final_gate()["final_gate_status"] == "LIVE_BLOCKED"
    assert write_rehearsal_report()["live_promotion_status"] == "LIVE_BLOCKED"
    state = Supervisor().run_once()
    assert state.canary_rehearsal_summary["live_promotion_status"] == "LIVE_BLOCKED"
