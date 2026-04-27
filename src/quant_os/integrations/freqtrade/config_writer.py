from __future__ import annotations

import json
from pathlib import Path


def write_freqtrade_dry_run_config(
    output_path: str | Path = "reports/integrations/freqtrade_dry_run_config.json",
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    config = {
        "dry_run": True,
        "trading_mode": "spot",
        "max_open_trades": 1,
        "stake_amount": 10,
        "exchange": {
            "name": "dry-run-placeholder",
            "key": "",
            "secret": "",
        },
        "live_trading_allowed": False,
        "withdrawal_permissions": False,
    }
    path.write_text(json.dumps(config, indent=2, sort_keys=True), encoding="utf-8")
    return path
