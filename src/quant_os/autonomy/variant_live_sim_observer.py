from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.autonomy.variant_live_sim_common import build_variant_observations
from quant_os.research.strategy_factory.campaign_common import safe_payload, write_json_md


def write_variant_live_sim_observer_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    observations = build_variant_observations()
    payload = safe_payload(
        status="VARIANT_LIVE_SIM_OBSERVER_READY",
        observations=observations,
        observation_count=len(observations),
    )
    return write_json_md(
        payload,
        output_root=output_root,
        report_dir="live_sim",
        json_name="latest_observer.json",
        md_name="latest_observer.md",
        title="Variant Live Sim Observer",
        lines=[f"Status: {payload['status']}", f"Observations: {len(observations)}"],
    )
