from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any

from quant_os.security.config_guard import GuardResult, load_config_tree

KEY_PATTERN = re.compile(r"(api[_-]?key|secret|token|password)", re.IGNORECASE)
SUSPICIOUS_VALUE = re.compile(r"^[A-Za-z0-9_\-]{24,}$")


def secrets_guard(config_dir: str | Path = "configs") -> GuardResult:
    reasons: list[str] = []
    warnings: list[str] = []
    configs = load_config_tree(config_dir)
    for path, value in _find_secret_like_values(configs):
        if value:
            warnings.append(f"SUSPICIOUS_CONFIG_SECRET:{path}")
    for key, value in os.environ.items():
        if KEY_PATTERN.search(key) and SUSPICIOUS_VALUE.match(value or ""):
            warnings.append(f"SUSPICIOUS_ENV_SECRET:{key}")
    if _git_tracks_env():
        reasons.append("ENV_FILE_TRACKED_BY_GIT")
    withdrawal_paths = _find_withdrawal_settings(configs)
    reasons.extend(f"WITHDRAWAL_SETTING_PRESENT:{path}" for path in withdrawal_paths)
    return GuardResult(
        passed=not reasons,
        reasons=reasons,
        details={"warnings": warnings, "checked": "secrets_guard"},
    )


def _find_secret_like_values(value: Any, prefix: str = "") -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if KEY_PATTERN.search(str(key)) and isinstance(item, str):
                found.append((path, item))
            found.extend(_find_secret_like_values(item, path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_find_secret_like_values(item, f"{prefix}[{index}]"))
    return found


def _find_withdrawal_settings(value: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            key_text = str(key).lower()
            if (
                "withdraw" in key_text
                and not key_text.startswith("require_no_")
                and not (key_text == "withdrawal_permissions_allowed" and item is False)
                and not (key_text == "withdrawals_allowed" and item is False)
            ):
                found.append(path)
            found.extend(_find_withdrawal_settings(item, path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_find_withdrawal_settings(item, f"{prefix}[{index}]"))
    return found


def _git_tracks_env() -> bool:
    try:
        result = subprocess.run(
            ["git", "ls-files", ".env"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return False
    return bool(result.stdout.strip())
