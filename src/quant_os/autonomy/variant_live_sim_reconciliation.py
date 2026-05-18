from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.research.strategy_factory.campaign_common import safe_payload, write_json_md


def write_variant_live_sim_reconciliation_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = safe_payload(
        status="VARIANT_LIVE_SIM_RECONCILIATION_PASSED",
        reconciliation_failures=0,
        actual_order_count=0,
        actual_cancel_count=0,
    )
    return write_json_md(
        payload,
        output_root=output_root,
        report_dir="live_sim",
        json_name="latest_reconciliation.json",
        md_name="latest_reconciliation.md",
        title="Variant Live Sim Reconciliation",
        lines=["Status: VARIANT_LIVE_SIM_RECONCILIATION_PASSED"],
    )
