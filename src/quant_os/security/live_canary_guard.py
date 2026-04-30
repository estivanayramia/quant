from __future__ import annotations

from pathlib import Path

from quant_os.canary.policy import load_canary_config
from quant_os.security.config_guard import GuardResult
from quant_os.security.live_trading_guard import live_trading_guard

BLOCKED_TRUE_FLAGS = {
    "enabled": "CANARY_ENABLED_TRUE",
    "live_trading_allowed": "CANARY_LIVE_TRADING_ALLOWED_TRUE",
    "paper_trading_allowed": "CANARY_PAPER_TRADING_ALLOWED_TRUE",
    "exchange_keys_allowed": "CANARY_EXCHANGE_KEYS_ALLOWED_TRUE",
    "withdrawal_permissions_allowed": "CANARY_WITHDRAWAL_PERMISSIONS_ALLOWED_TRUE",
    "futures_allowed": "CANARY_FUTURES_ALLOWED_TRUE",
    "margin_allowed": "CANARY_MARGIN_ALLOWED_TRUE",
    "leverage_allowed": "CANARY_LEVERAGE_ALLOWED_TRUE",
    "shorting_allowed": "CANARY_SHORTING_ALLOWED_TRUE",
    "options_allowed": "CANARY_OPTIONS_ALLOWED_TRUE",
}


def live_canary_guard(config_path: str | Path = "configs/live_canary.yaml") -> GuardResult:
    config = load_canary_config(config_path)
    reasons: list[str] = []
    for key, reason in BLOCKED_TRUE_FLAGS.items():
        if config.get(key) is True:
            reasons.append(reason)
    if config.get("dry_run_required") is not True:
        reasons.append("CANARY_DRY_RUN_NOT_REQUIRED")
    if config.get("human_approval_required") is not True:
        reasons.append("CANARY_HUMAN_APPROVAL_NOT_REQUIRED")
    live_guard = live_trading_guard()
    reasons.extend(live_guard.reasons)
    return GuardResult(
        passed=not reasons,
        reasons=reasons,
        details={"checked": "live_canary_guard", "live_promotion_status": "LIVE_BLOCKED"},
    )
