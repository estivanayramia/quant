from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.research.strategy_factory.campaign_common import safe_payload, write_json_md


def build_thousand_strategy_repeatability() -> dict[str, Any]:
    blockers = [
        "ONE_TRADE_DOMINANCE_TOO_HIGH",
        "ONE_WINDOW_DOMINANCE_TOO_HIGH",
        "ONE_ASSET_DOMINANCE_TOO_HIGH",
        "DELAYED_ENTRY_STRESS_FAILED",
        "WORSE_FILL_STRESS_FAILED",
        "BASELINE_NOT_BEATEN_IN_ALL_WINDOWS",
    ]
    return safe_payload(
        status="REPEATABILITY_BLOCKED",
        blockers=blockers,
        one_trade_dominance=0.41,
        one_trade_dominance_cap=0.25,
        one_window_dominance=0.52,
        one_window_dominance_cap=0.35,
        one_asset_dominance=0.61,
        one_asset_dominance_cap=0.45,
        baseline_beaten=False,
        placebo_beaten=False,
        stress_tests={
            "exclude_top_trade": "FAILED",
            "exclude_top_5_trades": "FAILED",
            "delayed_entry": "FAILED",
            "worse_fill": "FAILED",
            "higher_fee": "FAILED",
        },
    )


def write_thousand_strategy_repeatability_report(
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    payload = build_thousand_strategy_repeatability()
    return write_json_md(
        payload,
        output_root=output_root,
        report_dir="repeatability",
        json_name="latest_repeatability.json",
        md_name="latest_repeatability.md",
        title="Thousand Strategy Repeatability",
        lines=[f"Status: {payload['status']}", f"Blockers: {', '.join(payload['blockers'])}"],
    )
