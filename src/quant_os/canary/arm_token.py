from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from quant_os.canary.policy import CANARY_ROOT, write_canary_report
from quant_os.data.loaders import load_yaml
from quant_os.governance.two_step_approval import write_approval_rehearsal

ARM_JSON = CANARY_ROOT / "latest_arm_token.json"
ARM_MD = CANARY_ROOT / "latest_arm_token.md"


def generate_arm_token(write: bool = True) -> dict[str, Any]:
    config = load_yaml("configs/canary_rehearsal.yaml") if Path("configs/canary_rehearsal.yaml").exists() else {}
    minutes = int(config.get("arming", {}).get("token_expiry_minutes", 15))
    generated_at = datetime.now(UTC)
    token_material = uuid.uuid4().hex
    payload = {
        "status": "PASS",
        "token_id": f"arm_{token_material[:12]}",
        "token_hash": hashlib.sha256(token_material.encode("utf-8")).hexdigest(),
        "generated_at": generated_at.isoformat(),
        "expires_at": (generated_at + timedelta(minutes=minutes)).isoformat(),
        "dual_confirmation_required": True,
        "rehearsal_only": True,
        "live_unlocked": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "blockers": [],
        "warnings": ["Arming token is rehearsal-only and cannot enable live trading."],
        "next_commands": [
            "make.cmd canary-preflight-rehearsal",
            "make.cmd canary-rehearsal",
        ],
    }
    if write:
        write_canary_report(ARM_JSON, ARM_MD, "Canary Arm Token Rehearsal", payload)
        write_approval_rehearsal()
    return payload


def validate_arm_token(record: dict[str, Any] | None = None, path: str | Path = ARM_JSON) -> dict[str, Any]:
    payload = record if record is not None else _load_token_report(path)
    if not payload:
        return {
            "status": "FAIL",
            "blockers": ["ARM_TOKEN_MISSING"],
            "warnings": [],
            "live_unlocked": False,
            "live_promotion_status": "LIVE_BLOCKED",
        }
    blockers = []
    if payload.get("rehearsal_only") is not True:
        blockers.append("ARM_TOKEN_NOT_REHEARSAL_ONLY")
    if payload.get("live_unlocked") is True:
        blockers.append("ARM_TOKEN_ATTEMPTED_LIVE_UNLOCK")
    expires_at = payload.get("expires_at")
    if not expires_at:
        blockers.append("ARM_TOKEN_EXPIRY_MISSING")
    else:
        try:
            expiry = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=UTC)
            if expiry <= datetime.now(UTC):
                blockers.append("ARM_TOKEN_EXPIRED")
        except ValueError:
            blockers.append("ARM_TOKEN_EXPIRY_INVALID")
    return {
        "status": "FAIL" if blockers else "PASS",
        "token_id": payload.get("token_id"),
        "blockers": blockers,
        "warnings": payload.get("warnings", []),
        "live_unlocked": False,
        "live_promotion_status": "LIVE_BLOCKED",
    }


def _load_token_report(path: str | Path) -> dict[str, Any] | None:
    report_path = Path(path)
    if not report_path.exists():
        return None
    try:
        return json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
