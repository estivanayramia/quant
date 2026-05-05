from __future__ import annotations

from quant_os.live_canary.notional_limits import validate_notional_limit
from quant_os.security.config_guard import GuardResult


def live_notional_guard(notional_usd: float) -> GuardResult:
    payload = validate_notional_limit(notional_usd)
    return GuardResult(
        passed=payload["status"] == "PASS",
        reasons=list(payload["blockers"]),
        details=payload,
    )

