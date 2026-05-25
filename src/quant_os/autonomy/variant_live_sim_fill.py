from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.autonomy.variant_live_sim_common import build_variant_fills
from quant_os.research.strategy_factory.campaign_common import safe_payload, write_json_md


def write_variant_live_sim_fill_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    fills = build_variant_fills()
    fake_fills = [fill for fill in fills if fill["fill_type"] != "fake_no_fill"]
    payload = safe_payload(
        status="VARIANT_LIVE_SIM_FILLS_APPLIED",
        fake_fills=fake_fills,
        fake_fill_count=len(fake_fills),
        fake_no_fill_count=len(fills) - len(fake_fills),
        guaranteed_fill=False,
    )
    return write_json_md(
        payload,
        output_root=output_root,
        report_dir="live_sim",
        json_name="latest_fills.json",
        md_name="latest_fills.md",
        title="Variant Live Sim Fills",
        lines=[f"Status: {payload['status']}", f"Fake fills: {len(fake_fills)}"],
    )
