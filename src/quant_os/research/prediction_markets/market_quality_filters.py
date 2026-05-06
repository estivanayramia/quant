from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from quant_os.data.prediction_markets.activity_capture import build_activity_dataset_from_capture

REPORT_ROOT = Path("reports/sequence27/market_quality")
MARKET_QUALITY_FILTER_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
}


def evaluate_market_quality_filters(dataset: dict[str, Any]) -> dict[str, Any]:
    rows = [_market_quality(market) for market in dataset["markets"]]
    included = [row for row in rows if row["included_in_lane_activity_research"]]
    usable = [row for row in included if row["usable_for_signal_testing"]]
    flagged = [row for row in rows if row["quality_flags"]]
    warnings = []
    if len(usable) < len(included):
        warnings.append("FILTERING_REDUCES_SAMPLE_SIZE")
    if any("MISSING_REFERENCE_CONTEXT" in row["quality_flags"] for row in rows):
        warnings.append("MISSING_REFERENCE_CONTEXT_PRESENT")
    return {
        "sequence": "27",
        "source": dataset["source"],
        "source_mode": dataset["source_mode"],
        "lane_id": dataset["lane_id"],
        "dataset_id": dataset["dataset_id"],
        "dataset_hash": dataset["dataset_hash"],
        "market_quality_status": "MARKET_QUALITY_FILTERED_RESEARCH_ONLY",
        "summary": {
            "market_count": len(rows),
            "included_market_count": len(included),
            "quality_filtered_count": len(usable),
            "flagged_market_count": len(flagged),
            "excluded_from_signal_testing_count": len(rows) - len(usable),
        },
        "flag_counts": dict(
            sorted(Counter(flag for row in rows for flag in row["quality_flags"]).items())
        ),
        "warnings": warnings,
        "market_quality": rows,
        "observed_facts": [
            "Market-quality filters are deterministic research diagnostics.",
            "Filters do not create trade commands, sizing rules, or execution authority.",
        ],
        "inferred_patterns": [
            "Filtering improves research honesty while reducing the usable sample.",
        ],
        "unknowns": [
            "Market-quality filters are not venue-mechanics replay or fill simulation.",
        ],
        **MARKET_QUALITY_FILTER_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_market_quality_filter_report(
    *,
    fixture_path: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    dataset = build_activity_dataset_from_capture(fixture_path)
    payload = evaluate_market_quality_filters(dataset)
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _market_quality(market: dict[str, Any]) -> dict[str, Any]:
    activity = market.get("activity") or []
    flags = []
    if not market["included_in_lane_activity_research"]:
        flags.append(str(market.get("exclusion_reason") or "EXCLUDED"))
    if not market.get("reference_context"):
        flags.append("MISSING_REFERENCE_CONTEXT")
    if (
        market["resolution"]["status"] == "RESOLVED"
        and market["resolution"].get("confidence") != "HIGH"
    ):
        flags.append("WEAK_RESOLUTION_LABEL_CONFIDENCE")
    if len(activity) < 5:
        flags.append("ACTIVITY_HISTORY_TOO_SHALLOW")
    if _max_unsupported_jump(activity) >= 0.08:
        flags.append("JUMP_WITHOUT_SUPPORTING_LIQUIDITY")
    if _max_concentration(activity) >= 0.68:
        flags.append("CONCENTRATION_SPIKE")
    if _min_liquidity(activity) < 8000:
        flags.append("SUSPICIOUS_THINNESS")
    resolved = market["resolution"]["status"] == "RESOLVED"
    severe = {
        "AMBIGUOUS",
        "DISPUTED",
        "OUTSIDE_TARGET_LANE",
        "MISSING_REFERENCE_CONTEXT",
        "WEAK_RESOLUTION_LABEL_CONFIDENCE",
        "ACTIVITY_HISTORY_TOO_SHALLOW",
        "JUMP_WITHOUT_SUPPORTING_LIQUIDITY",
        "CONCENTRATION_SPIKE",
        "SUSPICIOUS_THINNESS",
    }
    usable = bool(
        market["included_in_lane_activity_research"]
        and resolved
        and not (set(flags) & severe)
    )
    return {
        "market_id": market["market_id"],
        "condition_id": market["condition_id"],
        "slug": market["slug"],
        "category": market["category"],
        "included_in_lane_activity_research": market["included_in_lane_activity_research"],
        "resolution_status": market["resolution"]["status"],
        "quality_flags": sorted(set(flags)),
        "usable_for_signal_testing": usable,
        "exclusion_reason": market.get("exclusion_reason"),
        "activity_count": len(activity),
        "max_unsupported_price_jump": round(_max_unsupported_jump(activity), 6),
        "max_wallet_concentration": round(_max_concentration(activity), 6),
        "min_liquidity": round(_min_liquidity(activity), 6),
    }


def _max_unsupported_jump(activity: list[dict[str, Any]]) -> float:
    if len(activity) < 2:
        return 0.0
    jumps = []
    for prior, current in zip(activity, activity[1:], strict=False):
        price_delta = abs(float(current["yes_price"]) - float(prior["yes_price"]))
        liquidity_delta = float(current["liquidity"]) - float(prior["liquidity"])
        if liquidity_delta <= 0:
            jumps.append(price_delta)
    return max(jumps or [0.0])


def _max_concentration(activity: list[dict[str, Any]]) -> float:
    return max([float(item["wallet_concentration"]) for item in activity] or [0.0])


def _min_liquidity(activity: list[dict[str, Any]]) -> float:
    return min([float(item["liquidity"]) for item in activity] or [0.0])


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_market_quality.json"
    md_path = root / "latest_market_quality.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 27 Market Quality Filters",
        "",
        "Research-only market-quality report. No execution authority.",
        "",
        f"Lane: {payload['lane_id']}",
        f"Market quality: {payload['market_quality_status']}",
        f"Quality-filtered observations: {payload['summary']['quality_filtered_count']}",
        f"Flagged markets: {payload['summary']['flagged_market_count']}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Observed facts",
    ]
    lines.extend(f"- {item}" for item in payload["observed_facts"])
    lines.extend(["", "## Inferred patterns"])
    lines.extend(f"- {item}" for item in payload["inferred_patterns"])
    lines.extend(["", "## Unknowns"])
    lines.extend(f"- {item}" for item in payload["unknowns"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
