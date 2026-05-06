from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from quant_os.data.prediction_markets.activity_capture import build_activity_dataset_from_capture

REPORT_ROOT = Path("reports/sequence26/dataset")
RESOLVED_HISTORY_GROWTH_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
}


def evaluate_resolved_history_growth(
    *,
    previous_dataset: dict[str, Any],
    expanded_dataset: dict[str, Any],
) -> dict[str, Any]:
    previous_summary = _summary(previous_dataset)
    expanded_summary = _summary(expanded_dataset)
    resolved_delta = (
        expanded_summary["usable_resolved_market_count"]
        - previous_summary["usable_resolved_market_count"]
    )
    status = (
        "RESOLVED_HISTORY_EXPANDED_RESEARCH_ONLY"
        if resolved_delta > 0
        else "RESOLVED_HISTORY_NOT_EXPANDED"
    )
    return {
        "sequence": "26",
        "source": expanded_dataset["source"],
        "source_mode": expanded_dataset["source_mode"],
        "lane_id": expanded_dataset["lane_id"],
        "resolved_history_status": status,
        "dataset_id": expanded_dataset["dataset_id"],
        "dataset_hash": expanded_dataset["dataset_hash"],
        "previous_dataset_id": previous_dataset["dataset_id"],
        "previous_dataset_hash": previous_dataset["dataset_hash"],
        "market_delta": expanded_summary["market_count"] - previous_summary["market_count"],
        "resolved_delta": resolved_delta,
        "activity_observation_delta": (
            expanded_summary["activity_observation_count"]
            - previous_summary["activity_observation_count"]
        ),
        "previous_summary": previous_summary,
        "expanded_summary": expanded_summary,
        "inclusion_exclusion_summary": _exclusion_summary(expanded_dataset),
        "observed_facts": [
            "Sequence 26 compares saved Phase 25 real-cached activity to the expanded lane artifact.",
            "Only saved artifacts are used; no network fetch is required for CI or smoke targets.",
        ],
        "inferred_patterns": [
            "Resolved-history growth improves OOS research only when label quality and baseline comparisons hold up.",
        ],
        "unknowns": [
            "More resolved observations do not imply edge, replay readiness, or profitability.",
        ],
        "ready_for_narrow_replay_design": False,
        **RESOLVED_HISTORY_GROWTH_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_resolved_history_growth_report(
    *,
    previous_fixture_path: str | Path,
    expanded_fixture_path: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    previous_dataset = build_activity_dataset_from_capture(previous_fixture_path)
    expanded_dataset = build_activity_dataset_from_capture(expanded_fixture_path)
    payload = evaluate_resolved_history_growth(
        previous_dataset=previous_dataset,
        expanded_dataset=expanded_dataset,
    )
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _summary(dataset: dict[str, Any]) -> dict[str, Any]:
    usable_resolved = [
        market
        for market in dataset["markets"]
        if market["included_in_lane_activity_research"]
        and market["resolution"]["status"] == "RESOLVED"
    ]
    return {
        "dataset_id": dataset["dataset_id"],
        "dataset_hash": dataset["dataset_hash"],
        "market_count": dataset["market_count"],
        "included_market_count": dataset["included_market_count"],
        "resolved_market_count": dataset["resolved_market_count"],
        "usable_resolved_market_count": len(usable_resolved),
        "unresolved_market_count": dataset["unresolved_market_count"],
        "ambiguous_market_count": dataset["ambiguous_market_count"],
        "excluded_market_count": dataset["excluded_market_count"],
        "activity_observation_count": dataset["activity_observation_count"],
        "raw_event_count": dataset.get("raw_event_count", dataset["activity_observation_count"]),
        "usable_event_count": dataset.get(
            "usable_event_count",
            dataset["activity_observation_count"],
        ),
    }


def _exclusion_summary(dataset: dict[str, Any]) -> dict[str, int]:
    counts = Counter(
        market["exclusion_reason"]
        for market in dataset["markets"]
        if not market["included_in_lane_activity_research"]
    )
    return dict(sorted(counts.items()))


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_resolved_history_growth.json"
    md_path = root / "latest_resolved_history_growth.md"
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    lines = [
        "# Sequence 26 Resolved History Growth",
        "",
        "Research-only resolved-history growth report. No execution authority.",
        "",
        f"Lane: {payload['lane_id']}",
        f"Status: {payload['resolved_history_status']}",
        f"Market delta: {payload['market_delta']}",
        f"Resolved delta: {payload['resolved_delta']}",
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
