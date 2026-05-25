from __future__ import annotations

from typing import Any

from quant_os.readiness.canary_readiness_common import safety_payload


def evaluate_fire_drill_kill_switch(
    *,
    watcher_status: str = "eligible",
    reconciliation_status: str = "FAKE_RECONCILIATION_PASSED",
    unknown_fake_position: bool = False,
    manual_kill: bool = False,
    exception_raised: bool = False,
    live_trading_enabled: bool = False,
) -> dict[str, Any]:
    blockers: list[str] = []
    if watcher_status in {"stale", "missing forecast", "spread too wide", "price moved"}:
        blockers.append(watcher_status.upper().replace(" ", "_"))
    if reconciliation_status != "FAKE_RECONCILIATION_PASSED":
        blockers.append("RECONCILIATION_MISMATCH")
    if unknown_fake_position:
        blockers.append("UNKNOWN_FAKE_POSITION")
    if manual_kill:
        blockers.append("MANUAL_KILL")
    if exception_raised:
        blockers.append("EXCEPTION_SELF_DISABLE")
    if live_trading_enabled:
        blockers.append("LIVE_TRADING_FLAG_TRUE")
    return safety_payload(
        schema_version="autonomous_fire_drill_kill_switch_v1",
        status="FIRE_DRILL_KILL_SWITCH_BLOCKED" if blockers else "FIRE_DRILL_KILL_SWITCH_PASSED",
        allowed_statuses=["FIRE_DRILL_KILL_SWITCH_PASSED", "FIRE_DRILL_KILL_SWITCH_BLOCKED"],
        self_disabled=bool(blockers),
        blockers=blockers,
        request_signing_enabled=False,
        api_keys_loaded=False,
        private_keys_loaded=False,
        next_action="Remain disabled until deterministic blocker clears." if blockers else "Proceed.",
    )
