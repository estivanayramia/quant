from __future__ import annotations

from typing import Any

from quant_os.canary.policy import CANARY_ROOT, write_canary_report

STOPLOSS_JSON = CANARY_ROOT / "latest_stoploss_proof.json"
STOPLOSS_MD = CANARY_ROOT / "latest_stoploss_proof.md"


def build_stoploss_proof(write: bool = True) -> dict[str, Any]:
    payload = {
        "status": "FUTURE_PROOF_REQUIRED",
        "design_status": "DESIGNED_BUT_UNPROVEN",
        "required_future": True,
        "live_trading_enabled": False,
        "what_future_adapters_must_prove": [
            "exchange supports native stoploss orders for the selected spot pair",
            "stoploss order is acknowledged by exchange before entry is considered protected",
            "stoploss survives process restart and reconnect",
            "stoploss is visible in reconciliation artifacts",
            "manual cancel or missing stoploss triggers kill switch and quarantine",
        ],
        "proof_definition": [
            "documented exchange capability",
            "dry-run or paper artifact showing stoploss intent",
            "future exchange-side acknowledgment artifact before live canary",
            "reconciliation report linking entry to protective stop",
        ],
        "missing_evidence_today": [
            "no real exchange connectivity",
            "no exchange-side stoploss acknowledgment",
            "no live/paper stoploss reconciliation artifact",
        ],
        "failure_modes": [
            "entry opens without stoploss",
            "stoploss rejected or silently ignored",
            "network disconnect before protective order",
            "unsupported pair/order type",
            "manual cancel or stale state desync",
        ],
        "blockers": ["STOPLOSS_ON_EXCHANGE_NOT_PROVEN"],
        "warnings": [],
        "live_promotion_status": "LIVE_BLOCKED",
        "next_commands": ["make.cmd canary-preflight-rehearsal", "make.cmd canary-final-gate"],
    }
    if write:
        write_canary_report(STOPLOSS_JSON, STOPLOSS_MD, "Stoploss-On-Exchange Proof Design", payload)
    return payload
