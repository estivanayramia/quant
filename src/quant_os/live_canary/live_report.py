from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_os.live_canary.capabilities import inspect_exchange_capabilities
from quant_os.live_canary.live_preflight import prepare_live_canary, run_live_preflight
from quant_os.live_canary.live_reconcile import reconcile_live_canary
from quant_os.live_canary.live_status import live_canary_status
from quant_os.live_canary.reporting import LIVE_CANARY_ROOT, write_live_canary_report

REPORT_JSON = LIVE_CANARY_ROOT / "latest_report.json"
REPORT_MD = LIVE_CANARY_ROOT / "latest_report.md"


def write_live_canary_report_bundle(write: bool = True) -> dict[str, Any]:
    prepare = _load_or_build(LIVE_CANARY_ROOT / "latest_prepare.json", prepare_live_canary)
    capabilities = _load_or_build(
        LIVE_CANARY_ROOT / "latest_capabilities.json", inspect_exchange_capabilities
    )
    preflight = _load_or_build(LIVE_CANARY_ROOT / "latest_preflight.json", run_live_preflight)
    reconcile = _load_or_build(LIVE_CANARY_ROOT / "latest_reconciliation.json", reconcile_live_canary)
    status = _load_or_build(LIVE_CANARY_ROOT / "latest_status.json", live_canary_status)
    blockers = sorted(
        set(
            prepare.get("blockers", [])
            + preflight.get("blockers", [])
            + reconcile.get("blockers", [])
            + status.get("blockers", [])
        )
    )
    payload = {
        "status": "LIVE_BLOCKED" if blockers else "REPORT_READY",
        "generated_at": datetime.now(UTC).isoformat(),
        "mode": "blocked",
        "adapter_mode": capabilities.get("adapter_mode"),
        "dependency_status": capabilities.get("dependency_status"),
        "settings_status": capabilities.get("settings_status"),
        "capability_status": capabilities.get("status"),
        "prepare_status": prepare.get("status"),
        "preflight_status": preflight.get("preflight_status", preflight.get("status")),
        "reconciliation_status": reconcile.get("status"),
        "status_report_status": status.get("status"),
        "latest_report_path": str(REPORT_MD),
        "real_order_possible": False,
        "real_order_attempted": False,
        "blockers": blockers,
        "warnings": ["Report is observational and cannot fire live orders."],
        "live_promotion_status": "LIVE_BLOCKED",
        "next_commands": ["make.cmd canary-live-preflight", "make.cmd canary-live-stop"],
    }
    if write:
        write_live_canary_report(REPORT_JSON, REPORT_MD, "Live Canary Report", payload)
    return payload


def _load_or_build(path: Path, builder) -> dict[str, Any]:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return builder(write=True)
