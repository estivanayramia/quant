from __future__ import annotations

from quant_os.live_canary.exchange_fake import FakeLiveCanaryExchange
from quant_os.live_canary.live_fire import fire_live_canary


def test_fake_adapter_can_simulate_successful_attempt(local_project, tmp_path):
    adapter = FakeLiveCanaryExchange()
    payload = fire_live_canary(
        symbol="BTC/USDT",
        notional_usd=10,
        confirm_live_fire=True,
        adapter=adapter,
        allow_fake_gate_override=True,
        gate_override={"blockers": []},
        kill_switch_path=tmp_path / "kill.json",
    )
    assert payload["status"] == "FIRED"
    assert payload["fake_mode"] is True
    assert payload["real_order_attempted"] is False
    assert len(adapter.get_open_positions()) == 1

