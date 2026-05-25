from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.autonomy.canary_grade_live_sim_common import (
    ROOT,
    canary_safe_payload,
    cg_hash,
    update_state_from_payload,
)
from quant_os.autonomy.live_market_sim_common import load_json
from quant_os.readiness.canary_readiness_common import write_json_markdown_report

REPORT_DIR = ROOT / "crypto"


def build_crypto_canary_grade_ledger(
    *, output_root: str | Path = ".", fills_payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    fills_payload = fills_payload or load_json(
        "reports/canary_grade_live_sim/crypto/latest_fills.json",
        output_root=output_root,
    ) or {}
    entries = [
        {
            "ledger_entry_id": f"cgled_{cg_hash(fill)}",
            **fill,
            "fake_money": True,
            "no_transmit": True,
            "actual_order_count": 0,
            "actual_cancel_count": 0,
            "position_state": "OPEN_THEN_MARKED_FAKE",
        }
        for fill in list(fills_payload.get("fake_fills", []) or [])
    ]
    return canary_safe_payload(
        schema_version="crypto_canary_grade_ledger_v1",
        status="CANARY_GRADE_LEDGER_UPDATED",
        ledger_entries=entries,
        fake_fill_count=len(entries),
        blockers=[],
        next_action="Compute canary-grade fake PnL from future public marks.",
    )


def write_crypto_canary_grade_ledger_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_crypto_canary_grade_ledger(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_ledger.json",
        md_name="latest_ledger.md",
        title="Crypto Canary-Grade Ledger",
        summary="Fake ledger for canary-grade no-transmit crypto simulation.",
    )
    update_state_from_payload(output_root=output_root, payload=payload)
    return payload
