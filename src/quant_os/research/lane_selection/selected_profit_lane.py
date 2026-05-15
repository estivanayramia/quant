from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.research.lane_selection.profit_lane_tournament import (
    PROFIT_LANE_SAFETY,
    build_profit_lane_tournament,
)

REPORT_ROOT = Path("reports/sequence49/selected_lane")


def build_selected_profit_lane_handoff(
    *,
    tournament: dict[str, Any] | None = None,
) -> dict[str, Any]:
    tournament = tournament or build_profit_lane_tournament()
    selected = tournament["selected_lane"]
    if selected is None:
        return _no_selection_handoff(tournament)
    lane_id = str(selected["lane_id"])
    lane_spec = _lane_specific_handoff(lane_id)
    others = {
        lane["lane_id"]: {
            "status": lane["promotion_status"],
            "total_score": lane["total_score"],
            "reason": lane["rationale"],
            "blockers": lane["blockers"],
        }
        for lane in tournament["lanes"]
        if lane["lane_id"] != lane_id
    }
    return {
        "schema_version": "selected_profit_lane_handoff_v1",
        "sequence": "49",
        "selection_status": tournament["tournament_status"],
        "paper_proving_readiness": tournament["tournament_status"],
        "selected_lane_id": lane_id,
        "selected_lane": selected,
        "why_selected": selected["rationale"],
        "why_others_not_selected": others,
        "required_data": lane_spec["required_data"],
        "required_tests": lane_spec["required_tests"],
        "first_replay_schema_needed": lane_spec["first_replay_schema_needed"],
        "first_paper_proving_dataset_needed": lane_spec[
            "first_paper_proving_dataset_needed"
        ],
        "blockers": lane_spec["blockers"],
        "next_phase_recommendation": lane_spec["next_phase_recommendation"],
        "exact_next_command": "python -m quant_os.cli research selected-profit-lane",
        "profit_claim_made": False,
        **PROFIT_LANE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_selected_profit_lane_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_selected_profit_lane_handoff()
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _lane_specific_handoff(lane_id: str) -> dict[str, Any]:
    if lane_id == "pm_weather_forecast_market_mismatch":
        return {
            "required_data": [
                "forecast snapshots",
                "forecast source timestamp",
                "market metadata",
                "bucket/range rules",
                "price snapshots",
                "liquidity/spread",
                "resolution labels",
                "event timestamps",
            ],
            "required_tests": [
                "market_baseline",
                "forecast_baseline",
                "stale_forecast_placebo",
                "random_bucket_placebo",
                "timestamp_shift_placebo",
                "spread_liquidity_stress",
                "oos_by_event_or_date",
            ],
            "first_replay_schema_needed": {
                "schema_id": "weather_bucket_forecast_market_snapshot_v1",
                "fields": [
                    "event_id",
                    "market_id",
                    "bucket_rule",
                    "forecast_probability",
                    "forecast_source_ts",
                    "market_price_ts",
                    "best_bid",
                    "best_ask",
                    "spread",
                    "liquidity",
                    "resolution_label",
                ],
            },
            "first_paper_proving_dataset_needed": (
                "At least several resolved weather events with pre-market forecast snapshots, "
                "synchronized public market prices, spreads/liquidity, and labels."
            ),
            "blockers": ["NO_REAL_WEATHER_REPLAY_DATASET_CAPTURED_YET"],
            "next_phase_recommendation": "Build a public/read-only weather forecast replay dataset before any paper-profit claim.",
        }
    if lane_id == "pm_cross_market_equivalence_arbitrage":
        return {
            "required_data": [
                "market metadata",
                "semantic relation mapping",
                "orderbook snapshots",
                "fees/spreads/liquidity",
                "resolution labels",
                "timestamps",
            ],
            "required_tests": [
                "no_skill_baseline",
                "random_relation_placebo",
                "stale_relation_placebo",
                "market_mid_baseline",
                "fill_no_fill_model",
                "partial_fill_model",
                "oos_across_event_types",
            ],
            "first_replay_schema_needed": {"schema_id": "cross_market_relation_orderbook_snapshot_v1"},
            "first_paper_proving_dataset_needed": "Resolved relation-mapped market snapshots.",
            "blockers": ["RELATION_MAPPING_NOT_CAPTURED_YET"],
            "next_phase_recommendation": "Build relation mapping and resolved orderbook snapshots first.",
        }
    return {
        "required_data": [
            "public candles",
            "public orderbook snapshots if available",
            "fees",
            "spreads",
            "slippage assumptions",
            "timestamped signals",
            "baselines",
            "placebos",
            "walk-forward split",
        ],
        "required_tests": [
            "buy_and_hold_baseline",
            "no_skill_baseline",
            "random_timestamp_placebo",
            "sign_flip_placebo",
            "volatility_regime_placebo",
            "cost_slippage_sensitivity",
            "oos_walk_forward",
        ],
        "first_replay_schema_needed": {"schema_id": "crypto_spot_signal_bar_replay_v1"},
        "first_paper_proving_dataset_needed": "Public spot-only replay bars with costs and OOS splits.",
        "blockers": ["REAL_SPOT_REPLAY_DATASET_NOT_SELECTED_OR_CAPTURED_YET"],
        "next_phase_recommendation": "Build a spot-only replay dataset and run the paper harness.",
    }


def _no_selection_handoff(tournament: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "selected_profit_lane_handoff_v1",
        "sequence": "49",
        "selection_status": tournament["tournament_status"],
        "paper_proving_readiness": tournament["tournament_status"],
        "selected_lane_id": None,
        "selected_lane": None,
        "why_selected": "No lane passed source, validation, and safety filters.",
        "why_others_not_selected": {
            lane["lane_id"]: {
                "status": lane["promotion_status"],
                "total_score": lane["total_score"],
                "reason": lane["rationale"],
                "blockers": lane["blockers"],
            }
            for lane in tournament["lanes"]
        },
        "required_data": [],
        "required_tests": [],
        "first_replay_schema_needed": {},
        "first_paper_proving_dataset_needed": "No dataset until a lane passes selection.",
        "blockers": ["NO_TESTABLE_LANE_FOUND"],
        "next_phase_recommendation": "Do not paper trade; revisit public data feasibility.",
        "exact_next_command": "python -m quant_os.cli research profit-lane-tournament",
        "profit_claim_made": False,
        **PROFIT_LANE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_selected_profit_lane.json"
    md_path = root / "latest_selected_profit_lane.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 49 Selected Profit Lane",
        "",
        "Selected path-to-paper-proof handoff. No live or profitability claim.",
        "",
        f"Status: {payload['selection_status']}",
        f"Selected lane: {payload['selected_lane_id']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Required Data",
    ]
    lines.extend(f"- {item}" for item in payload["required_data"] or ["None"])
    lines.extend(["", "## Required Tests"])
    lines.extend(f"- {item}" for item in payload["required_tests"] or ["None"])
    lines.extend(["", "## Blockers"])
    lines.extend(f"- {item}" for item in payload["blockers"] or ["None"])
    lines.extend(["", "## Next Command", f"`{payload['exact_next_command']}`"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
