from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.research.strategy_factory.campaign_common import safe_payload, write_json_md


def build_thousand_strategy_repeatability(candidate: dict[str, Any] | None = None) -> dict[str, Any]:
    candidate = candidate or {}
    baseline_beaten = bool(candidate.get("baseline_beaten", False))
    placebo_beaten = bool(candidate.get("placebo_beaten", False))
    one_trade_dominance_cap = 0.25
    one_window_dominance_cap = 0.35
    one_asset_dominance_cap = 0.45
    one_trade_dominance = float(candidate.get("one_trade_dominance", 0.41))
    one_window_dominance = float(candidate.get("one_window_dominance", 0.52))
    one_asset_dominance = float(candidate.get("one_asset_dominance", 0.61))
    stress_tests = {
        "exclude_top_trade": "FAILED",
        "exclude_top_5_trades": "FAILED",
        "delayed_entry": "FAILED",
        "worse_fill": "FAILED",
        "higher_fee": "FAILED",
        **dict(candidate.get("stress_tests") or {}),
    }
    blockers = []
    if one_trade_dominance > one_trade_dominance_cap:
        blockers.append("ONE_TRADE_DOMINANCE_TOO_HIGH")
    if one_window_dominance > one_window_dominance_cap:
        blockers.append("ONE_WINDOW_DOMINANCE_TOO_HIGH")
    if one_asset_dominance > one_asset_dominance_cap:
        blockers.append("ONE_ASSET_DOMINANCE_TOO_HIGH")
    if stress_tests["delayed_entry"] != "PASSED":
        blockers.append("DELAYED_ENTRY_STRESS_FAILED")
    if stress_tests["worse_fill"] != "PASSED":
        blockers.append("WORSE_FILL_STRESS_FAILED")
    if not baseline_beaten:
        blockers.append("BASELINE_NOT_BEATEN_IN_ALL_WINDOWS")
    if not placebo_beaten:
        blockers.append("PLACEBO_NOT_BEATEN_IN_ALL_WINDOWS")
    return safe_payload(
        status="REPEATABILITY_PASSED" if not blockers else "REPEATABILITY_BLOCKED",
        blockers=blockers,
        one_trade_dominance=one_trade_dominance,
        one_trade_dominance_cap=one_trade_dominance_cap,
        one_window_dominance=one_window_dominance,
        one_window_dominance_cap=one_window_dominance_cap,
        one_asset_dominance=one_asset_dominance,
        one_asset_dominance_cap=one_asset_dominance_cap,
        baseline_beaten=baseline_beaten,
        placebo_beaten=placebo_beaten,
        stress_tests=stress_tests,
    )


def write_thousand_strategy_repeatability_report(
    *,
    output_root: str | Path = ".",
    candidate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = build_thousand_strategy_repeatability(candidate)
    return write_json_md(
        payload,
        output_root=output_root,
        report_dir="repeatability",
        json_name="latest_repeatability.json",
        md_name="latest_repeatability.md",
        title="Thousand Strategy Repeatability",
        lines=[f"Status: {payload['status']}", f"Blockers: {', '.join(payload['blockers'])}"],
    )
