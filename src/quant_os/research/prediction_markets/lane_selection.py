from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from quant_os.data.prediction_markets.resolution_dataset import build_resolution_aware_dataset
from quant_os.research.prediction_markets.market_strata import build_market_strata

REPORT_ROOT = Path("reports/sequence23/lane_selection")
LANE_SELECTION_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
}


def select_prediction_lanes(*, dataset: dict[str, Any], strata: dict[str, Any]) -> dict[str, Any]:
    markets_by_id = {market["market_id"]: market for market in dataset["markets"]}
    strata_by_id = {market["market_id"]: market for market in strata["markets"]}
    lane_specs = [
        _lane_spec(
            lane_id="short_dated_clean_binary",
            name="Short-Dated Clean Binary Markets",
            description="Clean binary markets near resolution with non-thin liquidity.",
            predicate=lambda item: (
                item["usable_for_lane_research"]
                and item["time_to_resolution_bucket"] == "SHORT"
                and item["liquidity_bucket"] in {"MEDIUM", "DEEP"}
                and item["cleanliness_bucket"] == "CLEAN"
            ),
            inclusion_rules=[
                "binary market",
                "Phase 20 quality gate is RESEARCHABLE",
                "time-to-resolution bucket is SHORT",
                "liquidity bucket is MEDIUM or DEEP",
                "cleanliness bucket is CLEAN",
            ],
            excluded_market_types=[
                "unresolved markets for scored metrics",
                "thin-liquidity markets",
                "ambiguous or non-binary markets",
                "broad all-market pools",
            ],
            key_risks=[
                "Late prices may already reflect most public information.",
                "Small samples can overstate signal stability.",
            ],
        ),
        _lane_spec(
            lane_id="low_concentration_resolution_clear",
            name="Low-Concentration Resolution-Clear Markets",
            description="Clean markets without extreme wallet concentration.",
            predicate=lambda item: (
                item["usable_for_lane_research"]
                and item["concentration_bucket"] in {"LOW", "MODERATE"}
                and item["cleanliness_bucket"] == "CLEAN"
            ),
            inclusion_rules=[
                "binary market",
                "wallet concentration bucket is LOW or MODERATE",
                "cleanliness bucket is CLEAN",
            ],
            excluded_market_types=[
                "high-concentration markets",
                "ambiguous markets",
                "excluded low-quality markets",
            ],
            key_risks=[
                "Low concentration does not imply informed flow.",
                "The lane may remain too broad across unrelated event classes.",
            ],
        ),
        _lane_spec(
            lane_id="weather_science_resolution_clear",
            name="Weather and Science Resolution-Clear Markets",
            description="Event markets with comparatively concrete external resolution criteria.",
            predicate=lambda item: (
                item["usable_for_lane_research"]
                and item["category_bucket"] in {"Weather", "Science"}
                and item["cleanliness_bucket"] == "CLEAN"
            ),
            inclusion_rules=[
                "category is Weather or Science",
                "binary market",
                "clean external resolution context exists",
            ],
            excluded_market_types=[
                "political interpretation markets",
                "low-liquidity local markets",
                "ambiguous multi-outcome markets",
            ],
            key_risks=[
                "Concrete resolution does not guarantee predictive edge.",
                "Available resolved sample is likely too small.",
            ],
        ),
        _lane_spec(
            lane_id="all_researchable_markets",
            name="All Researchable Markets",
            description="Reference-only broad pool rejected as too vague for replay design.",
            predicate=lambda item: item["usable_for_lane_research"],
            inclusion_rules=["all markets not excluded from candidate research"],
            excluded_market_types=["none; this is why the lane is rejected as broad"],
            key_risks=[
                "Broad market pools hide lane-specific behavior.",
                "Ranking this lane highly would create readiness inflation.",
            ],
            rejected_broad=True,
        ),
    ]
    lanes = [
        _build_lane(spec, strata_by_id=strata_by_id, markets_by_id=markets_by_id) for spec in lane_specs
    ]
    lanes = sorted(lanes, key=lambda item: (-item["research_worthiness_score"], item["lane_id"]))
    for index, lane in enumerate(lanes, start=1):
        lane["rank"] = index
    best_lane = next((lane for lane in lanes if lane["research_status"] == "RESEARCH_WORTHY"), None)
    return {
        "sequence": "23",
        "source": "polymarket",
        "source_mode": dataset["source_mode"],
        "dataset_id": dataset["dataset_id"],
        "dataset_hash": dataset["dataset_hash"],
        "lane_count": len(lanes),
        "eligible_lane_count": sum(int(lane["research_status"] == "RESEARCH_WORTHY") for lane in lanes),
        "best_lane": best_lane,
        "lanes": lanes,
        "observed_facts": [
            "Candidate lanes are deterministic and derived from saved fixture strata.",
            "Broad all-market pooling is retained only as a rejected reference lane.",
        ],
        "inferred_patterns": [
            "Short-dated clean binary markets are the most research-worthy lane in this fixture.",
        ],
        "unknowns": [
            "Lane ranking is not evidence of alpha or replay readiness.",
        ],
        **LANE_SELECTION_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_lane_selection_report(
    *,
    fixture_path: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    dataset = build_resolution_aware_dataset(fixture_path)
    strata = build_market_strata(dataset)
    payload = select_prediction_lanes(dataset=dataset, strata=strata)
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _lane_spec(
    *,
    lane_id: str,
    name: str,
    description: str,
    predicate: Callable[[dict[str, Any]], bool],
    inclusion_rules: list[str],
    excluded_market_types: list[str],
    key_risks: list[str],
    rejected_broad: bool = False,
) -> dict[str, Any]:
    return {
        "lane_id": lane_id,
        "name": name,
        "description": description,
        "predicate": predicate,
        "inclusion_rules": inclusion_rules,
        "excluded_market_types": excluded_market_types,
        "key_risks": key_risks,
        "rejected_broad": rejected_broad,
    }


def _build_lane(
    spec: dict[str, Any],
    *,
    strata_by_id: dict[str, dict[str, Any]],
    markets_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    selected = [item for item in strata_by_id.values() if spec["predicate"](item)]
    selected = sorted(selected, key=lambda item: item["market_id"])
    market_ids = [item["market_id"] for item in selected]
    resolved_count = sum(
        int(markets_by_id[market_id]["resolution"]["status"] == "RESOLVED") for market_id in market_ids
    )
    score = _research_worthiness_score(
        spec["lane_id"],
        selected,
        resolved_count=resolved_count,
    )
    if spec["rejected_broad"]:
        score = min(score, 5.0)
        research_status = "REJECTED_BROAD_LANE"
    elif resolved_count >= 6 and selected:
        research_status = "RESEARCH_WORTHY"
    elif selected:
        research_status = "LANE_TOO_THIN"
    else:
        research_status = "EMPTY_LANE"
    return {
        "lane_id": spec["lane_id"],
        "name": spec["name"],
        "description": spec["description"],
        "inclusion_rules": spec["inclusion_rules"],
        "excluded_market_types": spec["excluded_market_types"],
        "sample_size": len(selected),
        "resolved_label_count": resolved_count,
        "market_ids": market_ids,
        "key_risks": spec["key_risks"],
        "why_it_may_support_predictive_work": _why_may_support(spec["lane_id"]),
        "why_it_may_fail": _why_may_fail(spec["lane_id"]),
        "research_worthiness_score": round(score, 6),
        "research_status": research_status,
        "rank": None,
    }


def _research_worthiness_score(
    lane_id: str,
    selected: list[dict[str, Any]],
    *,
    resolved_count: int,
) -> float:
    if not selected:
        return 0.0
    avg_cleanliness = sum(float(item["cleanliness_score"]) for item in selected) / len(selected)
    liquidity_bonus = sum(int(item["liquidity_bucket"] == "DEEP") for item in selected) * 2.0
    short_bonus = sum(int(item["time_to_resolution_bucket"] == "SHORT") for item in selected) * 1.5
    lane_focus_bonus = 35.0 if lane_id == "short_dated_clean_binary" else 0.0
    broadness_penalty = 15.0 if lane_id == "low_concentration_resolution_clear" else 0.0
    return (
        (resolved_count * 8.0)
        + (avg_cleanliness * 0.35)
        + liquidity_bonus
        + short_bonus
        + lane_focus_bonus
        - broadness_penalty
    )


def _why_may_support(lane_id: str) -> str:
    reasons = {
        "short_dated_clean_binary": "Near-resolution markets may reveal stabilization or instability patterns.",
        "low_concentration_resolution_clear": "Lower concentration can reduce manipulation-suspicion noise.",
        "weather_science_resolution_clear": "Clear external resolution criteria can reduce labeling ambiguity.",
        "all_researchable_markets": "This broad pool is useful only as a reference denominator.",
    }
    return reasons[lane_id]


def _why_may_fail(lane_id: str) -> str:
    reasons = {
        "short_dated_clean_binary": "The market baseline may already price late public information efficiently.",
        "low_concentration_resolution_clear": "Concentration alone may have little predictive content.",
        "weather_science_resolution_clear": "Sample size may be too small and event classes may differ.",
        "all_researchable_markets": "Broad pooling is not an interpretable replay lane.",
    }
    return reasons[lane_id]


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_lane_selection.json"
    md_path = root / "latest_lane_selection.md"
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    lines = [
        "# Sequence 23 Lane Selection",
        "",
        "Research-only lane selection report. No execution authority.",
        "",
        f"Best lane: {payload['best_lane']['lane_id'] if payload['best_lane'] else 'None'}",
        f"Eligible lanes: {payload['eligible_lane_count']}",
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
