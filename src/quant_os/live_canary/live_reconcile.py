from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from quant_os.live_canary.adapter import build_live_canary_adapter
from quant_os.live_canary.capabilities import inspect_exchange_capabilities
from quant_os.live_canary.exchange_port import LiveCanaryExchangePort
from quant_os.live_canary.reporting import LIVE_CANARY_ROOT, write_live_canary_report

RECON_JSON = LIVE_CANARY_ROOT / "latest_reconciliation.json"
RECON_MD = LIVE_CANARY_ROOT / "latest_reconciliation.md"


def reconcile_live_canary(
    *,
    adapter: LiveCanaryExchangePort | None = None,
    expected_open_positions: int = 0,
    write: bool = True,
) -> dict[str, Any]:
    adapter = adapter or build_live_canary_adapter()
    capabilities = adapter.capabilities()
    capability_report = inspect_exchange_capabilities(write=True)
    positions = adapter.get_open_positions() if capabilities.adapter_available else []
    blockers: list[str] = []
    warnings: list[str] = []
    if not capabilities.adapter_available:
        warnings.append("LIVE_ADAPTER_UNAVAILABLE_FOR_RECONCILIATION")
    if len(positions) != expected_open_positions:
        blockers.append("LIVE_RECONCILIATION_POSITION_COUNT_MISMATCH")
    status = "FAIL" if blockers else ("WARN" if warnings else "PASS")
    payload = {
        "status": status,
        "generated_at": datetime.now(UTC).isoformat(),
        "mode": "fake" if getattr(adapter, "is_fake", False) else "blocked",
        "adapter_mode": capability_report["adapter_mode"],
        "dependency_status": capability_report["dependency_status"],
        "settings_status": capability_report["settings_status"],
        "capability_status": capability_report["status"],
        "adapter_available": capabilities.adapter_available,
        "expected_open_positions": expected_open_positions,
        "observed_open_positions": len(positions),
        "positions": [position.__dict__ for position in positions],
        "real_order_possible": False,
        "real_order_attempted": False,
        "blockers": blockers,
        "warnings": warnings,
        "live_promotion_status": "LIVE_BLOCKED",
        "next_commands": ["make.cmd canary-live-status", "make.cmd canary-live-report"],
    }
    if write:
        write_live_canary_report(RECON_JSON, RECON_MD, "Live Canary Reconciliation", payload)
    return payload

