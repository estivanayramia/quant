from __future__ import annotations

from quant_os.live_canary.exchange_fake import FakeLiveCanaryExchange
from quant_os.live_canary.exchange_port import ExchangePosition
from quant_os.live_canary.live_reconcile import reconcile_live_canary


def test_live_reconcile_passes_when_fake_state_matches(local_project):
    adapter = FakeLiveCanaryExchange(
        positions=[ExchangePosition(symbol="BTC/USDT", side="long", notional_usd=10)]
    )
    payload = reconcile_live_canary(adapter=adapter, expected_open_positions=1)
    assert payload["status"] == "PASS"


def test_live_reconcile_detects_mismatch(local_project):
    adapter = FakeLiveCanaryExchange(
        positions=[ExchangePosition(symbol="BTC/USDT", side="long", notional_usd=10)]
    )
    payload = reconcile_live_canary(adapter=adapter, expected_open_positions=0)
    assert payload["status"] == "FAIL"
    assert "LIVE_RECONCILIATION_POSITION_COUNT_MISMATCH" in payload["blockers"]

