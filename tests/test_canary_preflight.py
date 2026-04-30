from __future__ import annotations

from quant_os.canary.preflight import evaluate_canary_preflight


def test_canary_preflight_fails_closed_when_evidence_missing(local_project):
    payload = evaluate_canary_preflight()
    assert payload["status"] == "LIVE_BLOCKED"
    assert payload["preflight_status"] == "BLOCKED"
    assert payload["live_allowed"] is False
