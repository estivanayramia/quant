from __future__ import annotations

from quant_os.canary.preflight_rehearsal import run_preflight_rehearsal


def test_preflight_rehearsal_fails_closed_when_required_evidence_missing(local_project):
    payload = run_preflight_rehearsal()
    assert payload["status"] == "LIVE_BLOCKED"
    assert payload["preflight_rehearsal_status"] == "REHEARSAL_FAIL"
    assert "PERMISSION_MANIFEST_MISSING" in payload["blockers"]
    assert payload["no_exchange_connection"] is True
