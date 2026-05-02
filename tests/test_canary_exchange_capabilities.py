from __future__ import annotations

import yaml

from quant_os.live_canary.capabilities import inspect_exchange_capabilities


def test_capability_report_generated_in_fake_mode(local_project):
    payload = inspect_exchange_capabilities()
    assert payload["status"] == "FAKE_ONLY"
    assert payload["adapter_mode"] == "fake"
    assert payload["real_order_possible"] is False


def test_real_adapter_blocks_when_settings_path_inside_repo(local_project):
    settings = local_project / "settings.yaml"
    settings.write_text(
        yaml.safe_dump(
            {
                "exchange_name": "kraken",
                "account_mode": "spot_only",
                "stoploss_on_exchange_supported": True,
            }
        ),
        encoding="utf-8",
    )
    _write_real_mode(local_project, settings)
    payload = inspect_exchange_capabilities()
    assert payload["status"] == "REAL_ADAPTER_BLOCKED"
    assert "REAL_ADAPTER_SETTINGS_PATH_INSIDE_REPO" in payload["blockers"]


def test_real_adapter_blocks_when_account_mode_not_spot(local_project):
    settings = local_project.parent / "settings-margin.yaml"
    settings.write_text(
        yaml.safe_dump(
            {
                "exchange_name": "kraken",
                "account_mode": "margin",
                "stoploss_on_exchange_supported": True,
            }
        ),
        encoding="utf-8",
    )
    _write_real_mode(local_project, settings)
    payload = inspect_exchange_capabilities(settings_path=settings)
    assert "REAL_ADAPTER_ACCOUNT_MODE_NOT_SPOT_ONLY" in payload["blockers"]


def _write_real_mode(local_project, settings):
    (local_project / "configs/live_execution.yaml").write_text(
        yaml.safe_dump(
            {
                "enabled": False,
                "live_trading_allowed": False,
                "exchange_adapter_enabled": True,
                "exchange_name": "kraken",
                "spot_only": True,
                "allowed_symbols": ["BTC/USDT", "ETH/USDT"],
                "max_order_notional_usd": 25,
                "max_open_positions": 1,
                "allow_autonomous_start": False,
                "credentials": {
                    "local_file_required": True,
                    "env_allowed": False,
                    "repo_storage_allowed": False,
                },
                "execution": {"live_order_enabled": False, "emergency_stop_enabled": True},
                "adapter": {
                    "type": "real",
                    "real_adapter_enabled": True,
                    "real_adapter_name": "kraken_spot_ccxt",
                    "optional_dependency_required": True,
                    "capability_probe_enabled": True,
                    "live_transport_enabled": True,
                },
                "real_adapter": {
                    "local_settings_file_required": True,
                    "local_settings_inside_repo_allowed": False,
                    "local_settings_path": str(settings),
                    "account_mode": "spot_only",
                    "read_balance_allowed": True,
                    "trade_allowed": True,
                    "withdrawals_allowed": False,
                    "futures_allowed": False,
                    "margin_allowed": False,
                    "leverage_allowed": False,
                    "shorts_allowed": False,
                    "options_allowed": False,
                },
            }
        ),
        encoding="utf-8",
    )

