from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

APPROVALS_PATH = Path("reports/canary/approval_registry.json")


class ApprovalRecord(BaseModel):
    approval_id: str
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    approver_name: str = "HUMAN_PLACEHOLDER"
    rationale: str = ""
    scope: str = "tiny_live_crypto_canary_future"
    expiry: str | None = None
    acknowledged_risks: list[str] = Field(default_factory=list)
    revoked: bool = False
    revocation_note: str | None = None


def load_approvals(path: str | Path = APPROVALS_PATH) -> list[ApprovalRecord]:
    approval_path = Path(path)
    if not approval_path.exists():
        return []
    try:
        raw = json.loads(approval_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    records = raw.get("approvals", raw if isinstance(raw, list) else [])
    return [ApprovalRecord.model_validate(item) for item in records]


def write_approvals(records: list[ApprovalRecord], path: str | Path = APPROVALS_PATH) -> Path:
    approval_path = Path(path)
    approval_path.parent.mkdir(parents=True, exist_ok=True)
    approval_path.write_text(
        json.dumps({"approvals": [record.model_dump(mode="json") for record in records]}, indent=2),
        encoding="utf-8",
    )
    return approval_path


def evaluate_approval(records: list[ApprovalRecord] | None = None) -> dict[str, Any]:
    approvals = records if records is not None else load_approvals()
    now = datetime.now(UTC)
    blockers: list[str] = []
    active_records: list[dict[str, Any]] = []
    for record in approvals:
        record_blockers = _record_blockers(record, now)
        if record_blockers:
            blockers.extend(record_blockers)
        else:
            active_records.append(record.model_dump(mode="json"))
    if not approvals:
        blockers.append("HUMAN_APPROVAL_MISSING")
    return {
        "status": "PASS" if active_records else "FAIL",
        "approval_present": bool(active_records),
        "approvals_count": len(approvals),
        "active_approvals_count": len(active_records),
        "blockers": sorted(set(blockers)),
        "active_approvals": active_records,
        "live_promotion_status": "LIVE_BLOCKED",
        "live_unlocked": False,
    }


def _record_blockers(record: ApprovalRecord, now: datetime) -> list[str]:
    blockers: list[str] = []
    if record.revoked:
        blockers.append("HUMAN_APPROVAL_REVOKED")
    if not record.rationale:
        blockers.append("HUMAN_APPROVAL_RATIONALE_MISSING")
    if not record.expiry:
        blockers.append("HUMAN_APPROVAL_EXPIRY_MISSING")
    else:
        try:
            expiry = datetime.fromisoformat(record.expiry.replace("Z", "+00:00"))
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=UTC)
            if expiry <= now:
                blockers.append("HUMAN_APPROVAL_EXPIRED")
        except ValueError:
            blockers.append("HUMAN_APPROVAL_EXPIRY_INVALID")
    if len(record.acknowledged_risks) < 2:
        blockers.append("HUMAN_APPROVAL_RISK_ACKNOWLEDGEMENTS_MISSING")
    return blockers
