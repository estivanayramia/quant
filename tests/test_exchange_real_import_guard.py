from __future__ import annotations

import yaml

from quant_os.live_canary.exchange_real import KrakenSpotCanaryAdapter


def _write_real_config(local_project, settings_path=""):
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
                "execution": {
                    "dry_run_fallback_allowed": False,
                    "live_order_enabled": False,
                    "fire_command_requires_explicit_flag": True,
                    "double_confirmation_required": True,
                    "emergency_stop_enabled": True,
                },
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
                    "local_settings_path": str(settings_path),
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


def test_real_adapter_import_guard_blocks_when_dependency_missing(local_project, monkeypatch):
    import quant_os.live_canary.exchange_real as exchange_real

    monkeypatch.setattr(
        exchange_real,
        "ccxt_dependency_status",
        lambda: {"installed": False, "name": "ccxt", "blockers": ["CCXT_DEPENDENCY_MISSING"]},
    )
    _write_real_config(local_project)
    capabilities = KrakenSpotCanaryAdapter().capabilities()
    assert capabilities.adapter_available is False
    assert "CCXT_DEPENDENCY_MISSING" in capabilities.notes


def test_real_adapter_blocks_when_local_settings_missing(local_project):
    _write_real_config(local_project, settings_path=local_project.parent / "missing.yaml")
    capabilities = KrakenSpotCanaryAdapter(local_project.parent / "missing.yaml").capabilities()
    assert capabilities.adapter_available is False
    assert "REAL_ADAPTER_SETTINGS_FILE_MISSING" in capabilities.notes

