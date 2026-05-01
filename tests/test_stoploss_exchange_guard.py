from __future__ import annotations

from quant_os.live_canary.exchange_port import ExchangeCapabilities
from quant_os.security.stoploss_exchange_guard import stoploss_exchange_guard


def test_stoploss_guard_blocks_unknown_or_false_capability():
    assert not stoploss_exchange_guard(None).passed
    false_caps = ExchangeCapabilities(
        exchange_name="fake",
        adapter_available=True,
        supports_stoploss_on_exchange=False,
    )
    result = stoploss_exchange_guard(false_caps)
    assert not result.passed
    assert "STOPLOSS_ON_EXCHANGE_NOT_SUPPORTED" in result.reasons


def test_stoploss_guard_passes_only_when_explicit_true():
    caps = ExchangeCapabilities(
        exchange_name="fake",
        adapter_available=True,
        supports_stoploss_on_exchange=True,
    )
    assert stoploss_exchange_guard(caps).passed

