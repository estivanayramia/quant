from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from quant_os.data.loaders import load_yaml

DEFAULT_CONFIG_PATH = Path("freqtrade/user_data/config/config.dry-run.generated.json")
KEY_ENV_NAMES = [
    "EXCHANGE_API_KEY",
    "EXCHANGE_SECRET_KEY",
    "FREQTRADE_EXCHANGE_KEY",
    "FREQTRADE_EXCHANGE_SECRET",
    "KRAKEN_API_KEY",
    "KRAKEN_SECRET_KEY",
]


def write_freqtrade_dry_run_config(
    output_path: str | Path = DEFAULT_CONFIG_PATH,
    config_path: str | Path = "configs/freqtrade.yaml",
) -> Path:
    _reject_exchange_key_env()
    settings = load_yaml(config_path)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pairs = settings.get("pairs") or ["BTC/USDT", "ETH/USDT"]
    config: dict[str, Any] = {
        "dry_run": True,
        "live_trading_allowed": False,
        "operational_enabled": False,
        "autonomous_start_allowed": False,
        "trading_mode": "spot",
        "margin_mode": "",
        "max_open_trades": int(settings.get("max_open_trades", 1)),
        "stake_currency": str(settings.get("stake_currency", "USDT")),
        "stake_amount": float(settings.get("stake_amount", 10)),
        "timeframe": str(settings.get("timeframe", "5m")),
        "strategy": str(settings.get("strategy_name", "QuantOSDryRunStrategy")),
        "initial_state": str(settings.get("initial_state", "stopped")),
        "cancel_open_orders_on_exit": True,
        "force_entry_enable": False,
        "shorting": False,
        "futures": False,
        "leverage": 1,
        "exchange": {
            "name": str(settings.get("exchange", "kraken")),
            "key": "",
            "secret": "",
            "password": "",
            "uid": "",
            "pair_whitelist": pairs,
            "pair_blacklist": [],
        },
        "telegram": {"enabled": False},
        "api_server": {"enabled": False},
        "bot_name": "quant-os-dry-run",
        "internals": {"process_throttle_secs": 5},
    }
    path.write_text(json.dumps(config, indent=2, sort_keys=True), encoding="utf-8")
    return path


def load_generated_config(path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _reject_exchange_key_env() -> None:
    present = [name for name in KEY_ENV_NAMES if os.environ.get(name)]
    if present:
        msg = f"Refusing to generate Freqtrade config while exchange key env vars are present: {present}"
        raise RuntimeError(msg)
