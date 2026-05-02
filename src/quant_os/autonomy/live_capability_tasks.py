from __future__ import annotations

from typing import Any

from quant_os.live_canary.capabilities import inspect_exchange_capabilities


def live_capability_status() -> dict[str, Any]:
    capabilities = inspect_exchange_capabilities(write=True)
    return {
        "live_capabilities": {
            "adapter_mode": capabilities["adapter_mode"],
            "dependency_status": capabilities["dependency_status"],
            "settings_status": capabilities["settings_status"],
            "capability_status": capabilities["status"],
            "real_order_possible": capabilities["real_order_possible"],
            "live_promotion_status": "LIVE_BLOCKED",
            "latest_report_path": "reports/live_canary/latest_capabilities.md",
        }
    }

