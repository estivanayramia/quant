from __future__ import annotations

from pathlib import Path

from quant_os.canary.permissions_import import import_permission_manifest
from quant_os.security.config_guard import GuardResult


def permission_manifest_guard(path: str | Path | None = None) -> GuardResult:
    payload = import_permission_manifest(path=path or Path("__missing_permission_manifest__.yaml"), write=False)
    reasons = list(payload.get("blockers", [])) if payload["status"] != "PASS" else []
    return GuardResult(
        passed=not reasons,
        reasons=reasons,
        details=payload,
    )
