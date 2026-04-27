from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quant_os.adapters.event_store_jsonl import JsonlEventStore
from quant_os.core.events import EventType, make_event


class FreqtradeSafetyError(RuntimeError):
    pass


@dataclass
class FreqtradeSafetyResult:
    passed: bool
    reasons: list[str] = field(default_factory=list)
    config_path: str = ""


def validate_freqtrade_config(
    config_path: str | Path = "freqtrade/user_data/config/config.dry-run.generated.json",
    *,
    max_open_trades_limit: int = 1,
    max_stake_amount: float = 25.0,
    event_store: JsonlEventStore | None = None,
) -> FreqtradeSafetyResult:
    path = Path(config_path)
    reasons: list[str] = []
    if not _is_inside_config_dir(path):
        reasons.append("CONFIG_PATH_OUTSIDE_FREQTRADE_USER_CONFIG")
    if not path.exists():
        reasons.append("CONFIG_MISSING")
        return _finish(path, reasons, event_store)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("dry_run") is not True:
        reasons.append("DRY_RUN_NOT_TRUE")
    if payload.get("live_trading_allowed") is not False:
        reasons.append("LIVE_TRADING_ALLOWED")
    if payload.get("trading_mode") != "spot":
        reasons.append("TRADING_MODE_NOT_SPOT")
    if payload.get("margin_mode") not in {"", None}:
        reasons.append("MARGIN_MODE_ENABLED")
    if int(payload.get("max_open_trades", 999)) > max_open_trades_limit:
        reasons.append("MAX_OPEN_TRADES_TOO_HIGH")
    if float(payload.get("stake_amount", 999999)) > max_stake_amount:
        reasons.append("STAKE_AMOUNT_TOO_HIGH")
    if _has_secret(payload.get("exchange", {})):
        reasons.append("EXCHANGE_SECRET_PRESENT")
    if _nested_get(payload, ["telegram", "enabled"]) is not False:
        reasons.append("TELEGRAM_ENABLED")
    if _nested_get(payload, ["api_server", "enabled"]) is not False:
        reasons.append("API_SERVER_ENABLED")
    if payload.get("force_entry_enable") is not False:
        reasons.append("FORCE_ENTRY_ENABLED")
    if float(payload.get("leverage", 1) or 1) > 1:
        reasons.append("LEVERAGE_ABOVE_ONE")
    if payload.get("futures") is True or str(payload.get("trading_mode", "")).lower() == "futures":
        reasons.append("FUTURES_ENABLED")
    if payload.get("shorting") is True or payload.get("can_short") is True:
        reasons.append("SHORTING_ENABLED")
    if "dry_run_wallet" in payload:
        reasons.append("DRY_RUN_WALLET_PRESENT")
    return _finish(path, reasons, event_store)


def assert_freqtrade_config_safe(config_path: str | Path) -> FreqtradeSafetyResult:
    result = validate_freqtrade_config(config_path)
    if not result.passed:
        raise FreqtradeSafetyError(";".join(result.reasons))
    return result


def _finish(
    path: Path,
    reasons: list[str],
    event_store: JsonlEventStore | None,
) -> FreqtradeSafetyResult:
    result = FreqtradeSafetyResult(passed=not reasons, reasons=reasons, config_path=str(path))
    if event_store is not None and reasons:
        event_store.append(
            make_event(
                EventType.WATCHDOG_FAILED,
                "freqtrade-safety",
                {"reasons": reasons, "config_path": str(path)},
            )
        )
    if reasons:
        raise FreqtradeSafetyError(";".join(reasons))
    return result


def _is_inside_config_dir(path: Path) -> bool:
    root = (Path.cwd() / "freqtrade/user_data/config").resolve()
    try:
        path.resolve().relative_to(root)
    except ValueError:
        return False
    return True


def _has_secret(exchange: Any) -> bool:
    if not isinstance(exchange, dict):
        return True
    secret_fields = {"key", "secret", "password", "uid", "api_key", "api_secret"}
    for key, value in exchange.items():
        if str(key).lower() in secret_fields and str(value or "").strip():
            return True
    return False


def _nested_get(payload: dict[str, Any], path: list[str]) -> Any:
    current: Any = payload
    for item in path:
        if not isinstance(current, dict):
            return None
        current = current.get(item)
    return current
