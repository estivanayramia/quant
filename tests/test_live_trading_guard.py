from __future__ import annotations

from quant_os.security.live_trading_guard import live_trading_guard


def test_live_trading_guard_passes_safe_defaults(local_project, monkeypatch):
    monkeypatch.setenv("ENABLE_LIVE_TRADING", "false")
    assert live_trading_guard().passed


def test_live_trading_guard_rejects_env_true(local_project, monkeypatch):
    monkeypatch.setenv("ENABLE_LIVE_TRADING", "true")
    result = live_trading_guard()
    assert not result.passed
    assert "ENV_ENABLE_LIVE_TRADING_TRUE" in result.reasons
