from __future__ import annotations

import pytest

from quant_os.integrations.telegram.alert_adapter import TelegramAlertAdapter


def test_telegram_mock_alerts_only():
    adapter = TelegramAlertAdapter(enabled=False)
    assert adapter.send_summary("hello")
    assert adapter.sent_messages == ["MOCK_TELEGRAM:hello"]


def test_telegram_cannot_mutate_trading_state():
    adapter = TelegramAlertAdapter(enabled=False)
    with pytest.raises(PermissionError):
        adapter.place_order()
    with pytest.raises(PermissionError):
        adapter.change_risk_limit()
    with pytest.raises(PermissionError):
        adapter.release_quarantine()
    with pytest.raises(PermissionError):
        adapter.disable_kill_switch()
