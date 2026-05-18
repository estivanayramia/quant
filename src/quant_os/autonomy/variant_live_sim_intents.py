from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.autonomy.variant_live_sim_common import build_variant_intents
from quant_os.research.strategy_factory.campaign_common import safe_payload, write_json_md


def write_variant_live_sim_intents_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    intents = build_variant_intents()
    payload = safe_payload(
        status="VARIANT_LIVE_SIM_INTENTS_READY",
        intents=intents,
        eligible_intent_count=len(intents),
        fake_money=True,
        no_transmit=True,
    )
    return write_json_md(
        payload,
        output_root=output_root,
        report_dir="live_sim",
        json_name="latest_intents.json",
        md_name="latest_intents.md",
        title="Variant Live Sim Intents",
        lines=[f"Status: {payload['status']}", f"Eligible intents: {len(intents)}"],
    )
