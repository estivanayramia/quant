from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.canary.permissions import evaluate_permission_manifest
from quant_os.security.config_guard import GuardResult


def permissions_guard(manifest: dict[str, Any] | str | Path | None = None) -> GuardResult:
    result = evaluate_permission_manifest(manifest)
    reasons = list(result.get("blockers", [])) if result["status"] == "FAIL" else []
    return GuardResult(
        passed=not reasons,
        reasons=reasons,
        details=result,
    )
