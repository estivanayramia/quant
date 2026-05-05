from __future__ import annotations

from quant_os.security.live_symbol_guard import live_symbol_guard


def test_live_symbol_guard_blocks_disallowed_symbols(local_project):
    result = live_symbol_guard("DOGE/USDT")
    assert not result.passed
    assert "LIVE_SYMBOL_NOT_ALLOWED" in result.reasons


def test_live_symbol_guard_allows_allowlist(local_project):
    assert live_symbol_guard("BTC/USDT").passed

