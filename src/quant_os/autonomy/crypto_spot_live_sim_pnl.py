from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.autonomy.live_market_sim_common import load_json
from quant_os.autonomy.multi_market_live_sim_common import ROOT, safe_report_payload
from quant_os.readiness.canary_readiness_common import write_json_markdown_report

REPORT_DIR = ROOT / "crypto_spot"


def build_crypto_spot_live_sim_pnl(
    *,
    output_root: str | Path = ".",
    ledger: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ledger = ledger or load_json(
        "reports/multi_market_live_sim/crypto_spot/latest_crypto_ledger.json",
        output_root=output_root,
    ) or {}
    rows: list[dict[str, Any]] = []
    blockers: list[str] = []
    gross = 0.0
    net = 0.0
    for entry in list(ledger.get("ledger_entries", []) or []):
        if str(entry.get("mark_timestamp")) <= str(entry.get("entry_timestamp")):
            blockers.append("LOOKAHEAD_MARK_NOT_AFTER_ENTRY")
            continue
        quantity = float(entry.get("quantity") or 0.0)
        entry_price = float(entry.get("entry_price") or 0.0)
        mark_price = float(entry.get("mark_price") or 0.0)
        side_multiplier = 1.0 if entry.get("side") == "buy" else -1.0
        gross_row = (mark_price - entry_price) * quantity * side_multiplier
        costs = (
            float(entry.get("spread_cost") or 0.0)
            + float(entry.get("slippage_cost") or 0.0)
            + float(entry.get("fee_cost") or 0.0)
        )
        net_row = gross_row - costs
        row = {
            **entry,
            "fake_gross_pnl": round(gross_row, 8),
            "fake_net_pnl": round(net_row, 8),
            "total_cost": round(costs, 8),
            "mark_source": "future_public_spot_price_after_entry_timestamp",
        }
        rows.append(row)
        gross += gross_row
        net += net_row
    if blockers:
        status = "CRYPTO_LIVE_SIM_PNL_BLOCKED"
    elif not rows:
        status = "CRYPTO_LIVE_SIM_PENDING_MARKS"
    else:
        status = "CRYPTO_LIVE_SIM_PNL_READY"
    return safe_report_payload(
        schema_version="crypto_spot_live_sim_pnl_v1",
        status=status,
        allowed_statuses=[
            "CRYPTO_LIVE_SIM_PNL_READY",
            "CRYPTO_LIVE_SIM_PENDING_MARKS",
            "CRYPTO_LIVE_SIM_PNL_BLOCKED",
        ],
        pnl_rows=rows,
        completed_mark_count=len(rows),
        pending_mark_count=0 if rows or blockers else len(ledger.get("ledger_entries", []) or []),
        fake_gross_pnl=round(gross, 8),
        fake_net_pnl=round(net, 8),
        blockers=list(dict.fromkeys(blockers)),
        next_action="Run crypto spot baseline/placebo comparison." if status == "CRYPTO_LIVE_SIM_PNL_READY" else "Collect future public marks.",
    )


def write_crypto_spot_live_sim_pnl_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_crypto_spot_live_sim_pnl(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_crypto_pnl.json",
        md_name="latest_crypto_pnl.md",
        title="Crypto Spot Live Sim PnL",
        summary="Fake PnL from public future marks only after each entry timestamp.",
    )
    return payload
