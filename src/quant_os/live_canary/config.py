from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.data.loaders import load_yaml

CONFIG_PATH = Path("configs/live_execution.yaml")


def load_live_execution_config(config_path: str | Path = CONFIG_PATH) -> dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        return {
            "enabled": False,
            "live_trading_allowed": False,
            "exchange_adapter_enabled": False,
            "exchange_name": "canary_exchange",
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
                "type": "fake",
                "real_adapter_enabled": False,
                "real_adapter_name": "kraken_spot_ccxt",
                "optional_dependency_required": True,
                "capability_probe_enabled": True,
                "live_transport_enabled": False,
            },
            "real_adapter": {
                "local_settings_file_required": True,
                "local_settings_inside_repo_allowed": False,
                "local_settings_path": "",
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
    return load_yaml(path)


def live_execution_safety_blockers(config: dict[str, Any] | None = None) -> list[str]:
    cfg = config or load_live_execution_config()
    blockers: list[str] = []
    if cfg.get("spot_only") is not True:
        blockers.append("LIVE_EXECUTION_SPOT_ONLY_NOT_TRUE")
    if cfg.get("allow_autonomous_start") is True:
        blockers.append("LIVE_EXECUTION_AUTONOMOUS_START_ENABLED")
    if int(cfg.get("max_open_positions", 0)) != 1:
        blockers.append("LIVE_EXECUTION_MAX_OPEN_POSITIONS_NOT_ONE")
    if float(cfg.get("max_order_notional_usd", 0)) > 25:
        blockers.append("LIVE_EXECUTION_NOTIONAL_CAP_TOO_HIGH")
    execution = cfg.get("execution", {})
    if execution.get("dry_run_fallback_allowed") is True:
        blockers.append("LIVE_EXECUTION_DRY_RUN_FALLBACK_ALLOWED")
    if execution.get("emergency_stop_enabled") is not True:
        blockers.append("LIVE_EXECUTION_EMERGENCY_STOP_DISABLED")
    credentials = cfg.get("credentials", {})
    if credentials.get("env_allowed") is True:
        blockers.append("LIVE_CREDENTIAL_ENV_ALLOWED")
    if credentials.get("repo_storage_allowed") is True:
        blockers.append("LIVE_CREDENTIAL_REPO_STORAGE_ALLOWED")
    return blockers

