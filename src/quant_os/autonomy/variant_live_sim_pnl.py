from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.autonomy.variant_live_sim_common import build_variant_pnl_rows
from quant_os.research.strategy_factory.campaign_common import safe_payload, write_json_md


def write_variant_live_sim_pnl_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    rows = build_variant_pnl_rows()
    lookahead = any(row["mark_timestamp"] <= row["entry_timestamp"] for row in rows)
    payload = safe_payload(
        status="VARIANT_LIVE_SIM_PNL_READY" if not lookahead else "VARIANT_LIVE_SIM_PNL_BLOCKED",
        pnl_rows=rows,
        completed_mark_count=len(rows),
        fake_net_pnl=round(sum(row["net_pnl"] for row in rows), 6),
        lookahead_detected=lookahead,
        mark_policy="future_public_marks_only",
    )
    return write_json_md(
        payload,
        output_root=output_root,
        report_dir="live_sim",
        json_name="latest_pnl.json",
        md_name="latest_pnl.md",
        title="Variant Live Sim PnL",
        lines=[f"Status: {payload['status']}", f"Fake net PnL: {payload['fake_net_pnl']}"],
    )
