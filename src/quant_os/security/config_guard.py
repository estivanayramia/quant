from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class GuardResult:
    passed: bool
    reasons: list[str] = field(default_factory=list)
    details: dict[str, object] = field(default_factory=dict)


def load_config_tree(config_dir: str | Path = "configs") -> dict[str, Any]:
    root = Path(config_dir)
    configs: dict[str, Any] = {}
    for path in sorted(root.glob("*.yaml")):
        configs[path.name] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return configs


def config_guard(config_dir: str | Path = "configs") -> GuardResult:
    configs = load_config_tree(config_dir)
    required = [
        "autonomy.yaml",
        "risk_limits.yaml",
        "execution.yaml",
        "integrations.yaml",
        "watchdog.yaml",
    ]
    reasons = [f"MISSING_CONFIG:{name}" for name in required if name not in configs]
    live_true_paths = _find_true_flags(
        configs, {"live_trading_enabled", "allow_live_trading", "live_trading_allowed"}
    )
    reasons.extend(f"LIVE_FLAG_TRUE:{path}" for path in live_true_paths)
    withdrawal_paths = _find_keys_containing(configs, "withdraw")
    reasons.extend(f"WITHDRAWAL_SETTING_PRESENT:{path}" for path in withdrawal_paths)
    return GuardResult(
        passed=not reasons, reasons=reasons, details={"config_files": sorted(configs)}
    )


def _find_true_flags(value: Any, names: set[str], prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if key in names and item is True:
                found.append(path)
            found.extend(_find_true_flags(item, names, path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_find_true_flags(item, names, f"{prefix}[{index}]"))
    return found


def _find_keys_containing(value: Any, needle: str, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            key_text = str(key).lower()
            if needle.lower() in key_text and not key_text.startswith("require_no_"):
                found.append(path)
            found.extend(_find_keys_containing(item, needle, path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_find_keys_containing(item, needle, f"{prefix}[{index}]"))
    return found
