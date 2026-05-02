from __future__ import annotations

from quant_os.live_canary.symbol_allowlist import validate_symbol_allowed
from quant_os.security.config_guard import GuardResult


def live_symbol_guard(symbol: str) -> GuardResult:
    payload = validate_symbol_allowed(symbol)
    return GuardResult(
        passed=payload["status"] == "PASS",
        reasons=list(payload["blockers"]),
        details=payload,
    )

