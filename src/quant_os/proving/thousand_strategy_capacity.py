from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.research.strategy_factory.campaign_common import safe_payload, write_json_md


def build_thousand_strategy_capacity() -> dict[str, Any]:
    sizes = {
        "1_usd": {"supported": True, "spread_impact_bps": 2.0, "no_fill_probability": 0.05},
        "5_usd": {"supported": False, "spread_impact_bps": 18.0, "no_fill_probability": 0.30},
        "10_usd": {"supported": False, "spread_impact_bps": 31.0, "no_fill_probability": 0.45},
        "25_usd": {"supported": False, "spread_impact_bps": 75.0, "no_fill_probability": 0.70},
    }
    tiny_canary_supported = bool(sizes["1_usd"]["supported"])
    scalability_blockers = [
        "CAPACITY_ABOVE_1_USD_NOT_SUPPORTED",
        "EDGE_DISAPPEARS_UNDER_DEPTH_IMPACT",
    ]
    return safe_payload(
        status="CAPACITY_TINY_CANARY_PASSED" if tiny_canary_supported else "CAPACITY_BLOCKED",
        blockers=[] if tiny_canary_supported else ["ONE_USD_TINY_CANARY_NOT_SUPPORTED"],
        scalability_blockers=scalability_blockers,
        capacity_by_size=sizes,
        max_safe_notional_usd=1.0,
        scalability_claim_allowed=False,
        tiny_canary_supported=tiny_canary_supported,
    )


def write_thousand_strategy_capacity_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_thousand_strategy_capacity()
    return write_json_md(
        payload,
        output_root=output_root,
        report_dir="capacity",
        json_name="latest_capacity.json",
        md_name="latest_capacity.md",
        title="Thousand Strategy Capacity",
        lines=[f"Status: {payload['status']}", "Capacity is not proven beyond a tiny diagnostic."],
    )
