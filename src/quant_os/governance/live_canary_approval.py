from __future__ import annotations

from quant_os.canary.approvals import evaluate_approval
from quant_os.security.config_guard import GuardResult


def live_canary_approval_guard() -> GuardResult:
    payload = evaluate_approval()
    reasons = list(payload.get("blockers", [])) if payload["status"] != "PASS" else []
    return GuardResult(
        passed=not reasons,
        reasons=reasons,
        details={**payload, "live_promotion_status": "LIVE_BLOCKED"},
    )
