from __future__ import annotations

from quant_os.live_canary.exchange_fake import FakeLiveCanaryExchange
from quant_os.live_canary.exchange_port import ExchangePosition
from quant_os.live_canary.live_fire import fire_live_canary


def test_live_fire_cannot_run_without_confirmation(local_project, tmp_path):
    payload = fire_live_canary(
        symbol="BTC/USDT",
        notional_usd=10,
        adapter=FakeLiveCanaryExchange(),
        allow_fake_gate_override=True,
        gate_override={"blockers": []},
        kill_switch_path=tmp_path / "kill.json",
    )
    assert payload["status"] == "BLOCKED"
    assert "LIVE_FIRE_CONFIRMATION_MISSING" in payload["blockers"]


def test_live_fire_cannot_exceed_notional_cap(local_project, tmp_path):
    payload = fire_live_canary(
        symbol="BTC/USDT",
        notional_usd=26,
        confirm_live_fire=True,
        adapter=FakeLiveCanaryExchange(),
        allow_fake_gate_override=True,
        gate_override={"blockers": []},
        kill_switch_path=tmp_path / "kill.json",
    )
    assert "LIVE_NOTIONAL_CAP_EXCEEDED" in payload["blockers"]


def test_live_fire_cannot_use_disallowed_symbol(local_project, tmp_path):
    payload = fire_live_canary(
        symbol="DOGE/USDT",
        notional_usd=10,
        confirm_live_fire=True,
        adapter=FakeLiveCanaryExchange(),
        allow_fake_gate_override=True,
        gate_override={"blockers": []},
        kill_switch_path=tmp_path / "kill.json",
    )
    assert "LIVE_SYMBOL_NOT_ALLOWED" in payload["blockers"]


def test_live_fire_cannot_run_with_existing_open_position(local_project, tmp_path):
    adapter = FakeLiveCanaryExchange(
        positions=[ExchangePosition(symbol="BTC/USDT", side="long", notional_usd=10)]
    )
    payload = fire_live_canary(
        symbol="ETH/USDT",
        notional_usd=10,
        confirm_live_fire=True,
        adapter=adapter,
        allow_fake_gate_override=True,
        gate_override={"blockers": []},
        kill_switch_path=tmp_path / "kill.json",
    )
    assert "LIVE_MAX_OPEN_POSITION_ALREADY_REACHED" in payload["blockers"]

