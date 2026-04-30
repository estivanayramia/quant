from __future__ import annotations

from pathlib import Path

from quant_os.canary.arm_token import generate_arm_token
from quant_os.canary.permissions_import import import_permission_manifest
from quant_os.canary.rehearsal import run_canary_rehearsal

FIXTURE = Path(__file__).parent / "fixtures" / "canary" / "permission_manifest_safe.yaml"


def test_missing_manifest_blocks_rehearsal(local_project):
    payload = run_canary_rehearsal()
    assert payload["status"] == "LIVE_BLOCKED"
    assert "PERMISSION_MANIFEST_MISSING" in payload["blockers"]


def test_canary_rehearsal_never_places_orders(local_project):
    import_permission_manifest(FIXTURE)
    generate_arm_token()
    payload = run_canary_rehearsal()
    assert payload["placed_orders"] == 0
    assert payload["exchange_connections"] == 0
    assert payload["live_promotion_status"] == "LIVE_BLOCKED"
