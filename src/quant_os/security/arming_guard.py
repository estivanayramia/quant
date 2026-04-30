from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.canary.arm_token import validate_arm_token
from quant_os.security.config_guard import GuardResult


def arming_guard(record: dict[str, Any] | None = None, path: str | Path | None = None) -> GuardResult:
    payload = validate_arm_token(record=record, path=path or "reports/canary/latest_arm_token.json")
    reasons = list(payload.get("blockers", [])) if payload["status"] != "PASS" else []
    return GuardResult(
        passed=not reasons,
        reasons=reasons,
        details=payload,
    )
