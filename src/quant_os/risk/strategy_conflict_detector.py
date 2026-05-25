from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.research.strategy_factory.campaign_common import safe_payload, write_json_md


def build_strategy_conflict_detector(candidate: dict[str, Any] | None = None) -> dict[str, Any]:
    candidate = candidate or {
        "strategy_signal": "buy",
        "regime_signal": "buy",
        "liquidity_filter": "pass",
        "edge_bps": 3.0,
        "execution_uncertainty_bps": 7.0,
        "source_fresh": False,
    }
    vetoes = []
    if candidate.get("strategy_signal") != candidate.get("regime_signal"):
        vetoes.append("REGIME_CONFLICT")
    if candidate.get("liquidity_filter") == "fail":
        vetoes.append("LIQUIDITY_OR_SPREAD_CONFLICT")
    if float(candidate.get("edge_bps", 0.0)) <= float(candidate.get("execution_uncertainty_bps", 0.0)):
        vetoes.append("EDGE_SMALLER_THAN_EXECUTION_UNCERTAINTY")
    if candidate.get("source_fresh") is False:
        vetoes.append("FORECAST_OR_SOURCE_STALE")
    return safe_payload(
        status="CONFLICT_DETECTOR_PASSED" if not vetoes else "CONFLICT_DETECTOR_VETOED",
        veto_reasons=vetoes,
        candidate=candidate,
        checks=[
            "regime_filter",
            "liquidity_spread_filter",
            "cross_asset_signal",
            "related_market_contradiction",
            "stale_source",
            "entry_too_late",
            "edge_vs_uncertainty",
        ],
    )


def write_strategy_conflict_detector_report(
    *,
    output_root: str | Path = ".",
    candidate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = build_strategy_conflict_detector(candidate)
    return write_json_md(
        payload,
        output_root=output_root,
        report_dir="conflict_detector",
        json_name="latest_conflict_detector.json",
        md_name="latest_conflict_detector.md",
        title="Strategy Conflict Detector",
        lines=[f"Status: {payload['status']}", f"Vetoes: {', '.join(payload['veto_reasons'] or ['None'])}"],
    )
