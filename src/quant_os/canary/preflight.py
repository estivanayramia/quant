from __future__ import annotations

from typing import Any

from quant_os.canary.checklist import build_canary_checklist
from quant_os.canary.policy import CANARY_ROOT, load_canary_config, write_canary_report
from quant_os.security.live_canary_guard import live_canary_guard
from quant_os.security.live_trading_guard import live_trading_guard

PREFLIGHT_JSON = CANARY_ROOT / "latest_preflight.json"
PREFLIGHT_MD = CANARY_ROOT / "latest_preflight.md"


def evaluate_canary_preflight(
    permission_manifest: dict[str, Any] | None = None,
    write: bool = True,
) -> dict[str, Any]:
    config = load_canary_config()
    checklist = build_canary_checklist(permission_manifest=permission_manifest, write=False)
    canary_guard = live_canary_guard()
    live_guard = live_trading_guard()
    blockers = list(checklist["blockers"])
    if not canary_guard.passed:
        blockers.extend(canary_guard.reasons)
    if not live_guard.passed:
        blockers.extend(live_guard.reasons)
    if config.get("enabled", False):
        blockers.append("CANARY_CONFIG_ENABLED_TRUE")
    if config.get("live_trading_allowed", False):
        blockers.append("CANARY_LIVE_TRADING_ALLOWED_TRUE")
    planning_status = "BLOCKED" if blockers else "DRY_RUN_PROVEN_BUT_LIVE_BLOCKED"
    payload = {
        "status": "LIVE_BLOCKED",
        "preflight_status": planning_status,
        "checklist_status": checklist["status"],
        "blockers": sorted(set(blockers)),
        "warnings": checklist["warnings"],
        "live_trading_enabled": False,
        "live_allowed": False,
        "no_real_orders_possible": True,
        "human_approval_required": bool(config.get("human_approval_required", True)),
        "stoploss_on_exchange_requirement": "FUTURE_REQUIRED_NOT_VERIFIED",
        "ip_allowlist_requirement": "FUTURE_REQUIRED_NOT_VERIFIED",
        "api_key_scope_verification": "REQUIRED_FOR_FUTURE_NOT_GRANTED",
        "live_promotion_status": "LIVE_BLOCKED",
        "next_commands": ["make.cmd canary-readiness", "make.cmd canary-report"],
    }
    if write:
        write_canary_report(PREFLIGHT_JSON, PREFLIGHT_MD, "Canary Preflight", payload)
    return payload
