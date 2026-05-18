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


def build_crypto_canary_grade_pnl(
    *, output_root: str | Path = ".", ledger: dict[str, Any] | None = None
) -> dict[str, Any]:
    ledger = ledger or load_json(
        "reports/canary_grade_live_sim/crypto/latest_ledger.json",
        output_root=output_root,
    ) or {}
    blockers: list[str] = []
    rows: list[dict[str, Any]] = []
    gross = 0.0
    net = 0.0
    for entry in list(ledger.get("ledger_entries", []) or []):
        if str(entry.get("mark_timestamp")) <= str(entry.get("entry_timestamp")):
            blockers.append("LOOKAHEAD_MARK_NOT_AFTER_ENTRY")
            continue
        quantity = float(entry.get("quantity") or 0.0)
        entry_price = float(entry.get("entry_price") or 0.0)
        mark_price = float(entry.get("mark_price") or 0.0)
        gross_row = (mark_price - entry_price) * quantity
        costs = (
            float(entry.get("spread_cost") or 0.0)
            + float(entry.get("slippage_cost") or 0.0)
            + float(entry.get("fee_cost") or 0.0)
        )
        net_row = gross_row - costs
        rows.append(
            {
                **entry,
                "fake_gross_pnl": round(gross_row, 8),
                "fake_net_pnl": round(net_row, 8),
                "total_cost": round(costs, 8),
                "mark_source": "future_public_spot_price_after_entry_timestamp",
            }
        )
        gross += gross_row
        net += net_row
    status = "CANARY_GRADE_PNL_BLOCKED" if blockers else "CANARY_GRADE_PNL_READY"
    if not rows and not blockers:
        status = "CANARY_GRADE_PNL_PENDING_MARKS"
    return canary_safe_payload(
        schema_version="crypto_canary_grade_pnl_v1",
        status=status,
        pnl_rows=rows,
        completed_mark_count=len(rows),
        fake_gross_pnl=round(gross, 8),
        fake_net_pnl=round(net, 8),
        gross_profit=round(sum(max(float(row["fake_net_pnl"]), 0.0) for row in rows), 8),
        gross_loss=round(abs(sum(min(float(row["fake_net_pnl"]), 0.0) for row in rows)), 8),
        assets_tested=sorted({row["symbol"] for row in rows}),
        strategy_families_tested=sorted({row["strategy"] for row in rows}),
        regime_buckets=sorted({row["regime"] for row in rows}),
        walk_forward_windows=sorted({row["walk_forward_window"] for row in rows}),
        blockers=list(dict.fromkeys(blockers)),
        next_action="Run repeatability and capacity hardening.",
    )


def write_crypto_canary_grade_pnl_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_crypto_canary_grade_pnl(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_pnl.json",
        md_name="latest_pnl.md",
        title="Crypto Canary-Grade PnL",
        summary="Canary-grade fake PnL from future public marks only.",
    )
    update_state_from_payload(output_root=output_root, payload=payload)
    return payload
