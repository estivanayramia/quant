from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from quant_os.security.config_guard import GuardResult, load_config_tree


def live_trading_guard(config_dir: str | Path = "configs") -> GuardResult:
    reasons: list[str] = []
    if os.environ.get("ENABLE_LIVE_TRADING", "false").lower() not in {"", "0", "false", "no"}:
        reasons.append("ENV_ENABLE_LIVE_TRADING_TRUE")
    configs = load_config_tree(config_dir)
    for path in _live_flags_true(configs):
        reasons.append(f"LIVE_TRADING_ENABLED:{path}")
    return GuardResult(
        passed=not reasons, reasons=reasons, details={"checked": "live_trading_guard"}
    )


def _live_flags_true(value: Any, prefix: str = "") -> list[str]:
    live_names = {"live_trading_enabled", "allow_live_trading", "live_trading_allowed"}
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if key in live_names and item is True:
                found.append(path)
            found.extend(_live_flags_true(item, path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_live_flags_true(item, f"{prefix}[{index}]"))
    return found
