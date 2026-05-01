from __future__ import annotations

from quant_os.live_canary.live_preflight import prepare_live_canary, run_live_preflight


def test_live_prepare_blocks_without_credentials(local_project):
    payload = prepare_live_canary()
    assert payload["status"] == "BLOCKED"
    assert "LIVE_CREDENTIAL_FILE_MISSING" in payload["blockers"]
    assert payload["real_order_possible"] is False


def test_live_preflight_fails_closed_when_evidence_missing(local_project):
    payload = run_live_preflight(symbol="BTC/USDT", notional_usd=10)
    assert payload["preflight_status"] == "PREFLIGHT_FAIL"
    assert "LIVE_ORDER_ENABLED_FALSE" in payload["blockers"]
    assert payload["real_order_attempted"] is False

