from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.autonomy.canary_grade_live_sim_common import (
    ROOT,
    canary_safe_payload,
    update_state_from_payload,
)
from quant_os.autonomy.live_market_sim_common import load_json
from quant_os.readiness.canary_readiness_common import write_json_markdown_report

REPORT_DIR = ROOT / "crypto"


def build_crypto_canary_grade_reconciliation(*, output_root: str | Path = ".") -> dict[str, Any]:
    intents = load_json("reports/canary_grade_live_sim/crypto/latest_intents.json", output_root=output_root) or {}
    fills = load_json("reports/canary_grade_live_sim/crypto/latest_fills.json", output_root=output_root) or {}
    ledger = load_json("reports/canary_grade_live_sim/crypto/latest_ledger.json", output_root=output_root) or {}
    pnl = load_json("reports/canary_grade_live_sim/crypto/latest_pnl.json", output_root=output_root) or {}
    blockers: list[str] = []
    if len(fills.get("fake_fills", []) or []) > len(intents.get("intents", []) or []):
        blockers.append("FILL_WITHOUT_INTENT")
    if len(fills.get("fake_fills", []) or []) != len(ledger.get("ledger_entries", []) or []):
        blockers.append("LEDGER_FILL_MISMATCH")
    if len(ledger.get("ledger_entries", []) or []) != len(pnl.get("pnl_rows", []) or []):
        blockers.append("PNL_LEDGER_MISMATCH")
    if pnl.get("status") == "CANARY_GRADE_PNL_BLOCKED":
        blockers.extend(pnl.get("blockers", []) or ["PNL_BLOCKED"])
    status = "CANARY_GRADE_RECONCILIATION_PASSED" if not blockers else "CANARY_GRADE_RECONCILIATION_FAILED"
    return canary_safe_payload(
        schema_version="crypto_canary_grade_reconciliation_v1",
        status=status,
        eligible_intent_count=int(intents.get("eligible_intent_count") or 0),
        fake_fill_count=int(fills.get("fake_fill_count") or 0),
        completed_mark_count=int(pnl.get("completed_mark_count") or 0),
        fake_net_pnl=float(pnl.get("fake_net_pnl") or 0.0),
        reconciliation_failures=len(blockers),
        blockers=blockers,
        next_action="Run canary-grade readiness.",
    )


def write_crypto_canary_grade_reconciliation_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_crypto_canary_grade_reconciliation(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_reconciliation.json",
        md_name="latest_reconciliation.md",
        title="Crypto Canary-Grade Reconciliation",
        summary="Reconciliation for canary-grade fake-money crypto simulation.",
    )
    update_state_from_payload(output_root=output_root, payload=payload)
    return payload
