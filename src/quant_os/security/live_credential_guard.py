from __future__ import annotations

from pathlib import Path

from quant_os.live_canary.credential_loader import load_live_credentials
from quant_os.security.config_guard import GuardResult


def live_credential_guard(
    credential_path: str | Path | None = None,
    *,
    repo_root: str | Path | None = None,
) -> GuardResult:
    payload = load_live_credentials(credential_path, repo_root=repo_root)
    reasons = list(payload.get("blockers", [])) if payload["status"] != "PASS" else []
    return GuardResult(passed=not reasons, reasons=reasons, details=payload)

