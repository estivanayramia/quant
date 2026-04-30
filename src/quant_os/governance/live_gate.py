from __future__ import annotations

from typing import Any

from quant_os.canary.readiness import evaluate_canary_readiness


def evaluate_live_gate() -> dict[str, Any]:
    readiness = evaluate_canary_readiness(write=False)
    return {
        "status": "LIVE_BLOCKED",
        "readiness_status": readiness["readiness_status"],
        "blockers": readiness["blockers"],
        "live_allowed": False,
        "reason": "Phase 11 policy gates do not implement live execution authority.",
    }
