from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from quant_os.data.prediction_markets.activity_history import (
    LANE_ACTIVITY_SAFETY,
    build_lane_activity_history,
)

REPORT_ROOT = Path("reports/sequence24/dataset")


def summarize_lane_timelines(dataset: dict[str, Any]) -> dict[str, Any]:
    market_summaries = [_market_timeline_summary(market) for market in dataset["markets"]]
    activity_counts = [item["activity_points"] for item in market_summaries]
    lifecycle_counts = Counter(
        observation["lifecycle_status"]
        for market in dataset["markets"]
        for observation in market["activity"]
    )
    return {
        "sequence": "24",
        "source": dataset["source"],
        "source_mode": dataset["source_mode"],
        "lane_id": dataset["lane_id"],
        "dataset_id": dataset["dataset_id"],
        "dataset_hash": dataset["dataset_hash"],
        "summary": {
            "market_count": dataset["market_count"],
            "included_market_count": dataset["included_market_count"],
            "resolved_market_count": dataset["resolved_market_count"],
            "activity_observation_count": dataset["activity_observation_count"],
            "min_observations_per_market": min(activity_counts) if activity_counts else 0,
            "max_observations_per_market": max(activity_counts) if activity_counts else 0,
            "lifecycle_status_counts": dict(sorted(lifecycle_counts.items())),
        },
        "markets": sorted(market_summaries, key=lambda item: item["market_id"]),
        "observed_facts": [
            "Timeline summaries use saved lane activity observations only.",
            "Resolved, unresolved, ambiguous, and excluded statuses remain visible.",
        ],
        "inferred_patterns": [
            "Markets with multiple near-close observations can support dynamic feature screening.",
        ],
        "unknowns": [
            "Activity points are snapshots, not a full order book or trade tape.",
        ],
        **LANE_ACTIVITY_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_lane_timeline_summary_report(
    *,
    fixture_path: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    dataset = build_lane_activity_history(fixture_path)
    payload = summarize_lane_timelines(dataset)
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _market_timeline_summary(market: dict[str, Any]) -> dict[str, Any]:
    activity = market["activity"]
    first = activity[0] if activity else {}
    latest = activity[-1] if activity else {}
    prices = [float(item["yes_price"]) for item in activity]
    liquidities = [float(item["liquidity"]) for item in activity]
    concentrations = [float(item["wallet_concentration"]) for item in activity]
    return {
        "market_id": market["market_id"],
        "lane_activity_status": market["lane_activity_status"],
        "resolution_status": market["resolution"]["status"],
        "activity_points": len(activity),
        "first_timestamp": first.get("timestamp"),
        "latest_timestamp": latest.get("timestamp"),
        "first_lifecycle_status": first.get("lifecycle_status"),
        "latest_lifecycle_status": latest.get("lifecycle_status"),
        "price_range": round(max(prices) - min(prices), 6) if prices else 0.0,
        "liquidity_change": round(liquidities[-1] - liquidities[0], 6) if liquidities else 0.0,
        "wallet_concentration_change": (
            round(concentrations[-1] - concentrations[0], 6) if concentrations else 0.0
        ),
        "exclusion_reason": market["exclusion_reason"],
    }


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_lane_timeline_summary.json"
    md_path = root / "latest_lane_timeline_summary.md"
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    lines = [
        "# Sequence 24 Lane Timeline Summary",
        "",
        "Research-only lane timeline summary. No execution authority.",
        "",
        f"Lane: {payload['lane_id']}",
        f"Markets: {payload['summary']['market_count']}",
        f"Included markets: {payload['summary']['included_market_count']}",
        f"Activity observations: {payload['summary']['activity_observation_count']}",
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
