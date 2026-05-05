from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_os.live_canary.adapter_settings import load_real_adapter_settings
from quant_os.live_canary.config import load_live_execution_config
from quant_os.live_canary.exchange_factory import build_exchange_adapter
from quant_os.live_canary.exchange_real import ccxt_dependency_status
from quant_os.live_canary.reporting import LIVE_CANARY_ROOT, write_live_canary_report

CAPABILITIES_JSON = LIVE_CANARY_ROOT / "latest_capabilities.json"
CAPABILITIES_MD = LIVE_CANARY_ROOT / "latest_capabilities.md"


def inspect_exchange_capabilities(
    *,
    settings_path: str | Path | None = None,
    write: bool = True,
) -> dict[str, Any]:
    config = load_live_execution_config()
    adapter_config = config.get("adapter", {})
    mode = str(adapter_config.get("type", "fake"))
    dependency = ccxt_dependency_status()
    settings = load_real_adapter_settings(settings_path)
    adapter = build_exchange_adapter(settings_path=settings_path)
    capabilities = adapter.capabilities()
    blockers: list[str] = []
    warnings: list[str] = []
    if mode == "fake":
        status = "FAKE_ONLY"
        warnings.append("Fake adapter is configured; no real order is possible.")
    else:
        blockers.extend(settings.get("blockers", []))
        blockers.extend(dependency.get("blockers", []))
        if adapter_config.get("real_adapter_enabled") is not True:
            blockers.append("REAL_ADAPTER_NOT_ENABLED")
        if adapter_config.get("live_transport_enabled") is not True:
            blockers.append("REAL_ADAPTER_LIVE_TRANSPORT_DISABLED")
        if capabilities.supports_stoploss_on_exchange is not True:
            blockers.append("STOPLOSS_ON_EXCHANGE_NOT_SUPPORTED")
        status = "REAL_ADAPTER_CAPABLE" if not blockers else "REAL_ADAPTER_BLOCKED"
    if config.get("live_trading_allowed") is True:
        blockers.append("LIVE_TRADING_ALLOWED_TRUE")
    real_order_possible = status == "REAL_ADAPTER_CAPABLE" and capabilities.adapter_available
    payload = {
        "status": status,
        "generated_at": datetime.now(UTC).isoformat(),
        "adapter_mode": mode,
        "fake_adapter_active": mode == "fake",
        "real_adapter_name": adapter_config.get("real_adapter_name", "kraken_spot_ccxt"),
        "dependency_status": "installed" if dependency["installed"] else "missing",
        "optional_dependency": dependency,
        "settings_status": settings["status"],
        "settings_present": settings["settings_present"],
        "settings_path": settings["settings_path"],
        "spot_only_configured": settings.get("account_mode") == "spot_only" or mode == "fake",
        "stoploss_on_exchange": capabilities.supports_stoploss_on_exchange,
        "live_transport_enabled": bool(adapter_config.get("live_transport_enabled", False)),
        "adapter_available": capabilities.adapter_available,
        "capabilities": capabilities.__dict__,
        "real_order_possible": real_order_possible,
        "real_order_attempted": False,
        "allowed_symbols": config.get("allowed_symbols", []),
        "max_order_notional_usd": config.get("max_order_notional_usd", 25),
        "blockers": sorted(set(blockers)),
        "warnings": warnings,
        "live_promotion_status": "LIVE_BLOCKED",
        "next_commands": ["make.cmd canary-live-prepare", "make.cmd canary-live-preflight"],
    }
    if write:
        write_live_canary_report(
            CAPABILITIES_JSON,
            CAPABILITIES_MD,
            "Live Canary Exchange Capabilities",
            payload,
        )
    return payload

