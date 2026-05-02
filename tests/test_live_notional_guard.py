from __future__ import annotations

from quant_os.security.live_notional_guard import live_notional_guard


def test_live_notional_guard_blocks_cap_exceedance(local_project):
    result = live_notional_guard(26)
    assert not result.passed
    assert "LIVE_NOTIONAL_CAP_EXCEEDED" in result.reasons


def test_live_notional_guard_allows_tiny_notional(local_project):
    assert live_notional_guard(10).passed

