from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from quant_os.live_canary.config import load_live_execution_config


def load_real_adapter_settings(
    settings_path: str | Path | None = None,
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    config = load_live_execution_config()
    real_config = config.get("real_adapter", {})
    configured_path = settings_path or real_config.get("local_settings_path") or None
    root = Path(repo_root or Path.cwd()).resolve()
    blockers: list[str] = []
    warnings: list[str] = []
    raw: dict[str, Any] = {}
    resolved: Path | None = None
    if not configured_path:
        blockers.append("REAL_ADAPTER_SETTINGS_FILE_MISSING")
        return _payload(blockers, warnings, None, raw, root)
    path = Path(configured_path).expanduser()
    try:
        resolved = path.resolve(strict=False)
    except OSError:
        blockers.append("REAL_ADAPTER_SETTINGS_PATH_UNRESOLVABLE")
        resolved = path
    if _is_relative_to(resolved, root):
        blockers.append("REAL_ADAPTER_SETTINGS_PATH_INSIDE_REPO")
    if not resolved.exists():
        blockers.append("REAL_ADAPTER_SETTINGS_FILE_MISSING")
        return _payload(blockers, warnings, resolved, raw, root)
    if _is_secret_like_path(resolved):
        blockers.append("REAL_ADAPTER_SETTINGS_SECRET_LIKE_PATH")
    try:
        raw = _read_settings(resolved)
    except (json.JSONDecodeError, yaml.YAMLError, OSError):
        blockers.append("REAL_ADAPTER_SETTINGS_MALFORMED")
    if raw:
        if raw.get("account_mode", real_config.get("account_mode")) != "spot_only":
            blockers.append("REAL_ADAPTER_ACCOUNT_MODE_NOT_SPOT_ONLY")
        for key in [
            "withdrawals_allowed",
            "futures_allowed",
            "margin_allowed",
            "leverage_allowed",
            "shorts_allowed",
            "options_allowed",
        ]:
            if raw.get(key, real_config.get(key)) is True:
                blockers.append(f"REAL_ADAPTER_{key.upper()}_TRUE")
        if raw.get("exchange_name", config.get("exchange_name")) != "kraken":
            blockers.append("REAL_ADAPTER_EXCHANGE_NOT_KRAKEN")
    return _payload(blockers, warnings, resolved, raw, root)


def _read_settings(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _payload(
    blockers: list[str],
    warnings: list[str],
    path: Path | None,
    raw: dict[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    return {
        "status": "PASS" if not blockers else "FAIL",
        "generated_at": datetime.now(UTC).isoformat(),
        "settings_path": str(path) if path else None,
        "repo_root": str(repo_root),
        "settings_present": bool(raw),
        "exchange_name": raw.get("exchange_name"),
        "account_mode": raw.get("account_mode"),
        "stoploss_on_exchange_supported": raw.get("stoploss_on_exchange_supported"),
        "live_transport_enabled": bool(raw.get("live_transport_enabled", False)),
        "blockers": sorted(set(blockers)),
        "warnings": warnings,
        "secrets_returned": False,
        "raw_settings_metadata": _safe_metadata(raw),
        "live_promotion_status": "LIVE_BLOCKED",
    }


def _safe_metadata(raw: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "exchange_name",
        "account_mode",
        "stoploss_on_exchange_supported",
        "live_transport_enabled",
        "read_balance_allowed",
        "trade_allowed",
        "withdrawals_allowed",
        "futures_allowed",
        "margin_allowed",
        "leverage_allowed",
        "shorts_allowed",
        "options_allowed",
    }
    return {key: value for key, value in raw.items() if key in allowed}


def _is_secret_like_path(path: Path) -> bool:
    lowered = path.name.lower()
    return any(token in lowered for token in [".env", "secret", "credential", "key"])


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True

