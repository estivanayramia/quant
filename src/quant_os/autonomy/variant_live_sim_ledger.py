from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.autonomy.variant_live_sim_common import build_variant_fills
from quant_os.research.strategy_factory.campaign_common import safe_payload, write_json_md


def write_variant_live_sim_ledger_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    ledger_entries = [fill for fill in build_variant_fills() if fill["fill_type"] != "fake_no_fill"]
    payload = safe_payload(
        status="VARIANT_LIVE_SIM_LEDGER_UPDATED",
        ledger_entries=ledger_entries,
        hidden_local_state_dependency=False,
    )
    return write_json_md(
        payload,
        output_root=output_root,
        report_dir="live_sim",
        json_name="latest_ledger.json",
        md_name="latest_ledger.md",
        title="Variant Live Sim Ledger",
        lines=[f"Status: {payload['status']}", f"Entries: {len(ledger_entries)}"],
    )
