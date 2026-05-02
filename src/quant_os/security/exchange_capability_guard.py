from __future__ import annotations

from quant_os.live_canary.capabilities import inspect_exchange_capabilities
from quant_os.security.config_guard import GuardResult


def exchange_capability_guard() -> GuardResult:
    payload = inspect_exchange_capabilities(write=False)
    reasons = []
    if payload["status"] not in {"FAKE_ONLY", "REAL_ADAPTER_CAPABLE"}:
        reasons.extend(payload.get("blockers", []))
    if payload.get("adapter_mode") != "fake" and payload.get("stoploss_on_exchange") is not True:
        reasons.append("STOPLOSS_ON_EXCHANGE_NOT_SUPPORTED")
    return GuardResult(
        passed=not reasons,
        reasons=sorted(set(reasons)),
        details=payload,
    )

