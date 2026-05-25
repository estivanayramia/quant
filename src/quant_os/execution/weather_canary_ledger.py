from __future__ import annotations

from hashlib import sha256
from typing import Any


def build_canary_ledger_events(
    *,
    evidence_hash: str,
    duplicate_idempotency_key: bool = False,
) -> list[dict[str, Any]]:
    base = sha256(evidence_hash.encode("utf-8")).hexdigest()[:16]
    keys = [f"{base}-{index}" for index in range(7)]
    if duplicate_idempotency_key:
        keys[-1] = keys[0]
    event_types = [
        "pre_trade_evidence_bundle",
        "order_intent_preview",
        "manual_approval_placeholder",
        "hypothetical_submitted_placeholder",
        "hypothetical_accepted_or_rejected_placeholder",
        "hypothetical_fill_or_no_fill_placeholder",
        "settlement_reconciliation_placeholder",
    ]
    return [
        {
            "event_type": event_type,
            "idempotency_key": key,
            "client_order_id": f"weather-canary-{base}",
            "evidence_hash": evidence_hash,
            "offline_only": True,
            "no_send": True,
        }
        for event_type, key in zip(event_types, keys, strict=True)
    ]
