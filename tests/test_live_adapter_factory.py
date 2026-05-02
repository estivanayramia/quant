from __future__ import annotations

import yaml

from quant_os.live_canary.exchange_factory import build_exchange_adapter
from quant_os.live_canary.exchange_fake import FakeLiveCanaryExchange
from quant_os.live_canary.exchange_real import KrakenSpotCanaryAdapter
from quant_os.live_canary.live_preflight import run_live_preflight


def test_adapter_factory_defaults_to_fake(local_project):
    assert isinstance(build_exchange_adapter(), FakeLiveCanaryExchange)


def test_adapter_factory_builds_blocked_real_adapter_when_explicit(local_project):
    (local_project / "configs/live_execution.yaml").write_text(
        yaml.safe_dump(
            {
                "enabled": False,
                "live_trading_allowed": False,
                "exchange_adapter_enabled": False,
                "exchange_name": "kraken",
                "adapter": {"type": "real", "real_adapter_enabled": False},
                "real_adapter": {"local_settings_path": ""},
            }
        ),
        encoding="utf-8",
    )
    assert isinstance(build_exchange_adapter(), KrakenSpotCanaryAdapter)


def test_real_adapter_path_remains_blocked_without_all_gates(local_project):
    (local_project / "configs/live_execution.yaml").write_text(
        yaml.safe_dump(
            {
                "enabled": False,
                "live_trading_allowed": False,
                "exchange_adapter_enabled": False,
                "exchange_name": "kraken",
                "spot_only": True,
                "allowed_symbols": ["BTC/USDT", "ETH/USDT"],
                "max_order_notional_usd": 25,
                "max_open_positions": 1,
                "adapter": {"type": "real", "real_adapter_enabled": False},
                "real_adapter": {"local_settings_path": ""},
                "execution": {"live_order_enabled": False, "emergency_stop_enabled": True},
                "credentials": {"env_allowed": False, "repo_storage_allowed": False},
            }
        ),
        encoding="utf-8",
    )
    payload = run_live_preflight(symbol="BTC/USDT", notional_usd=10)
    assert payload["preflight_status"] == "PREFLIGHT_FAIL"
    assert "LIVE_ORDER_ENABLED_FALSE" in payload["blockers"]

