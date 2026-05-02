from __future__ import annotations

from typing import Any

from quant_os.live_canary.capabilities import inspect_exchange_capabilities
from quant_os.live_canary.live_preflight import run_live_preflight
from quant_os.live_canary.live_reconcile import reconcile_live_canary
from quant_os.live_canary.live_status import live_canary_status


def live_canary_safe_status() -> dict[str, Any]:
    capabilities = inspect_exchange_capabilities(write=True)
    status = live_canary_status(write=True)
    preflight = run_live_preflight(write=True)
    reconciliation = reconcile_live_canary(write=True)
    return {
        "live_canary": {
            "adapter_mode": capabilities["adapter_mode"],
            "dependency_status": capabilities["dependency_status"],
            "settings_status": capabilities["settings_status"],
            "capability_status": capabilities["status"],
            "adapter_available": status["adapter_available"],
            "prepare_status": preflight["checks"].get("prepare_status"),
            "preflight_status": preflight["preflight_status"],
            "final_gate_status": preflight["checks"].get("final_gate"),
            "latest_attempt_status": status["latest_attempt_status"],
            "latest_reconciliation_status": reconciliation["status"],
            "kill_switch_status": status["kill_switch_status"],
            "live_fire_enabled": False,
            "blockers": sorted(set(status["blockers"] + preflight["blockers"])),
            "latest_report_path": "reports/live_canary/latest_report.md",
        }
    }

