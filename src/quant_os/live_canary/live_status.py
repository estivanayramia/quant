from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_os.governance.live_attempt_registry import latest_live_attempt
from quant_os.live_canary.adapter import build_live_canary_adapter
from quant_os.live_canary.capabilities import inspect_exchange_capabilities
from quant_os.live_canary.config import load_live_execution_config
from quant_os.live_canary.exchange_port import LiveCanaryExchangePort
from quant_os.live_canary.live_kill_switch import (
    KILL_SWITCH_PATH,
    activate_live_kill_switch,
    read_live_kill_switch,
)
from quant_os.live_canary.reporting import LIVE_CANARY_ROOT, write_live_canary_report

STATUS_JSON = LIVE_CANARY_ROOT / "latest_status.json"
STATUS_MD = LIVE_CANARY_ROOT / "latest_status.md"
STOP_JSON = LIVE_CANARY_ROOT / "latest_stop.json"
STOP_MD = LIVE_CANARY_ROOT / "latest_stop.md"


def live_canary_status(
    *,
    adapter: LiveCanaryExchangePort | None = None,
    write: bool = True,
) -> dict[str, Any]:
    config = load_live_execution_config()
    adapter = adapter or build_live_canary_adapter()
    capabilities = adapter.capabilities()
    capability_report = inspect_exchange_capabilities(write=True)
    positions = adapter.get_open_positions() if capabilities.adapter_available else []
    kill_switch = read_live_kill_switch()
    attempt = latest_live_attempt()
    blockers = []
    if kill_switch.get("active"):
        blockers.append("LIVE_KILL_SWITCH_ACTIVE")
    payload = {
        "status": "LIVE_BLOCKED"
        if blockers or not capabilities.adapter_available
        else "READY_FOR_PREFLIGHT_RECHECK",
        "generated_at": datetime.now(UTC).isoformat(),
        "mode": "fake" if getattr(adapter, "is_fake", False) else "blocked",
        "adapter_mode": capability_report["adapter_mode"],
        "dependency_status": capability_report["dependency_status"],
        "settings_status": capability_report["settings_status"],
        "capability_status": capability_report["status"],
        "adapter_available": capabilities.adapter_available,
        "open_position_count": len(positions),
        "latest_attempt_status": attempt.get("status") if attempt else None,
        "latest_reconciliation_status": _latest_report_status(
            LIVE_CANARY_ROOT / "latest_reconciliation.json"
        ),
        "kill_switch_status": kill_switch.get("status"),
        "live_fire_enabled": False,
        "allowed_symbols": config.get("allowed_symbols", []),
        "max_order_notional_usd": config.get("max_order_notional_usd", 25),
        "real_order_possible": False,
        "real_order_attempted": False,
        "blockers": blockers,
        "warnings": ["Status does not start live trading."],
        "live_promotion_status": "LIVE_BLOCKED",
        "next_commands": ["make.cmd canary-live-preflight", "make.cmd canary-live-report"],
    }
    if write:
        write_live_canary_report(STATUS_JSON, STATUS_MD, "Live Canary Status", payload)
    return payload


def stop_live_canary(
    *,
    reason: str = "manual canary-live-stop",
    adapter: LiveCanaryExchangePort | None = None,
    kill_switch_path: str | Path = KILL_SWITCH_PATH,
    write: bool = True,
) -> dict[str, Any]:
    adapter = adapter or build_live_canary_adapter()
    capability_report = inspect_exchange_capabilities(write=True)
    kill_switch = activate_live_kill_switch(reason=reason, path=kill_switch_path)
    adapter_stop = adapter.emergency_stop()
    payload = {
        "status": "STOPPED",
        "generated_at": datetime.now(UTC).isoformat(),
        "mode": "fake" if getattr(adapter, "is_fake", False) else "blocked",
        "adapter_mode": capability_report["adapter_mode"],
        "dependency_status": capability_report["dependency_status"],
        "settings_status": capability_report["settings_status"],
        "capability_status": capability_report["status"],
        "kill_switch_status": kill_switch["status"],
        "adapter_stop": adapter_stop,
        "real_order_possible": False,
        "real_order_attempted": False,
        "blockers": ["LIVE_KILL_SWITCH_ACTIVE"],
        "warnings": ["Live canary stop blocks subsequent live attempts."],
        "live_promotion_status": "LIVE_BLOCKED",
        "next_commands": ["make.cmd canary-live-status", "make.cmd canary-live-report"],
    }
    if write:
        write_live_canary_report(STOP_JSON, STOP_MD, "Live Canary Stop", payload)
    return payload


def _latest_report_status(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        import json

        return json.loads(path.read_text(encoding="utf-8")).get("status")
    except json.JSONDecodeError:
        return "UNREADABLE"

