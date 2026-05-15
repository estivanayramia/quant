from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.proving.paper_proving_harness import (
    build_fixture_safe_paper_proving_input,
    run_paper_proving_harness,
)
from quant_os.proving.profit_claim_guard import evaluate_profit_claim_guard
from quant_os.research.lane_selection.paper_profit_lane_models import (
    build_default_lane_universe,
    rank_paper_profit_lanes,
)
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/paper_profit_discovery/discovery_loop")


def run_paper_profit_discovery_loop(
    *,
    output_root: str | Path = ".",
    max_lanes: int = 10,
    max_promoted_lanes: int = 2,
    max_fixture_only_diagnostics: int = 3,
) -> dict[str, Any]:
    ranked = rank_paper_profit_lanes(build_default_lane_universe())
    evaluated: list[dict[str, Any]] = []
    promoted_lane_count = 0
    fixture_diagnostic_count = 0
    selected: dict[str, Any] | None = None
    for lane in ranked[:max_lanes]:
        lane_row = lane.to_report_dict()
        lane_row["mini_pack"] = build_candidate_mini_pack(lane.lane_id)
        if lane.status in {"PROMOTE_TO_DATA_CAPTURE", "PROMOTE_TO_PAPER_TEST"}:
            promoted_lane_count += 1
            if fixture_diagnostic_count < max_fixture_only_diagnostics:
                fixture_diagnostic_count += 1
                proving = run_paper_proving_harness(
                    build_fixture_safe_paper_proving_input(lane_id=lane.lane_id)
                )
                guard = evaluate_profit_claim_guard(proving)
                lane_row["paper_proving"] = {
                    "readiness_status": proving["readiness_status"],
                    "net_simulated_pnl_after_costs": proving["net_simulated_pnl_after_costs"],
                    "fill_adjusted_pnl": proving["fill_adjusted_pnl"],
                    "warnings": proving["warnings"],
                }
                lane_row["profit_claim_guard"] = guard
                lane_row["paper_profit_status"] = "PAPER_PROFIT_DIAGNOSTIC_ONLY"
                lane_row["upgrade_blockers"] = _upgrade_blockers(guard)
                lane_row["exact_next_commands"] = _exact_next_commands(lane.lane_id)
                if selected is None:
                    selected = lane_row
            else:
                lane_row["paper_profit_status"] = "PAPER_PROFIT_BLOCKED"
                lane_row["upgrade_blockers"] = ["fixture_only_diagnostic_limit_reached"]
        else:
            lane_row["paper_profit_status"] = "NO_TESTABLE_LANE_FOUND"
            lane_row["upgrade_blockers"] = list(lane.blockers) or [lane.status_reason]
        evaluated.append(lane_row)
        if promoted_lane_count >= max_promoted_lanes:
            break

    selected = selected or _first_rejected(evaluated)
    paper_status = selected.get("paper_profit_status", "NO_TESTABLE_LANE_FOUND")
    payload = {
        "schema_version": "paper_profit_discovery_loop_v1",
        "discovery_status": (
            "PAPER_PROFIT_DIAGNOSTIC_ONLY_FOUND"
            if paper_status == "PAPER_PROFIT_DIAGNOSTIC_ONLY"
            else "ALL_LANES_REJECTED_OR_RESEARCH_ONLY"
        ),
        "paper_profit_status": paper_status,
        "selected_lane_id": selected["lane_id"],
        "selected_lane_status": selected["status"],
        "selected_lane": selected,
        "bounded_limits": {
            "max_lanes": max_lanes,
            "max_promoted_lanes": max_promoted_lanes,
            "max_fixture_only_diagnostics": max_fixture_only_diagnostics,
        },
        "evaluated_lane_count": len(evaluated),
        "promoted_lane_count": promoted_lane_count,
        "fixture_only_diagnostic_count": fixture_diagnostic_count,
        "evaluated_lanes": evaluated,
        "stop_reason": (
            "diagnostic-only fixture pack requires public source capture before any profit claim"
            if paper_status == "PAPER_PROFIT_DIAGNOSTIC_ONLY"
            else "bounded lane set exhausted or blocked"
        ),
        "profitability_claimed": False,
        "paper_only": True,
        "ci_network_dependency": False,
        "evidence_only": True,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
    }
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def build_candidate_mini_pack(lane_id: str) -> dict[str, Any]:
    if lane_id in {"pm_weather_forecast_market_mismatch", "pm_market_bucket_boundary_mispricing"}:
        return _weather_mini_pack(lane_id)
    if lane_id == "pm_cross_market_equivalence_arbitrage":
        return _cross_market_mini_pack(lane_id)
    if lane_id.startswith("crypto_") or lane_id.startswith("btc_"):
        return _crypto_spot_mini_pack(lane_id)
    return {
        "lane_id": lane_id,
        "paper_only": True,
        "profit_claim_allowed": False,
        "required_data": [],
        "required_tests": [],
        "reason": "No candidate mini-pack because lane is blocked, deprioritized, or research-only.",
    }


def _weather_mini_pack(lane_id: str) -> dict[str, Any]:
    return {
        "lane_id": lane_id,
        "schema_version": "weather_forecast_market_mismatch_mini_pack_v1",
        "paper_only": True,
        "profit_claim_allowed": False,
        "required_data": [
            "forecast_snapshots",
            "forecast_timestamp",
            "market_metadata",
            "bucket_range_rules",
            "market_price_snapshots",
            "liquidity_spread",
            "resolution_labels",
        ],
        "schema_fields": [
            "event_id",
            "forecast_source",
            "forecast_timestamp",
            "forecast_bucket",
            "market_id",
            "bucket_rule",
            "best_bid",
            "best_ask",
            "spread",
            "liquidity",
            "resolution_label",
            "provenance_hash",
        ],
        "required_tests": [
            "market_baseline",
            "forecast_baseline",
            "stale_forecast_placebo",
            "random_bucket_placebo",
            "timestamp_shift_placebo",
            "spread_liquidity_stress",
            "oos_by_event_date",
        ],
        "fixture_safe_sample": [
            {
                "event_id": "fixture_weather_event_001",
                "forecast_source": "fixture_public_weather_shape",
                "forecast_timestamp": "2026-05-01T12:00:00Z",
                "forecast_bucket": "temperature_70_to_74",
                "market_id": "fixture_market_weather_bucket",
                "bucket_rule": "fixture range bucket",
                "best_bid": 0.40,
                "best_ask": 0.44,
                "spread": 0.04,
                "liquidity": 1000.0,
                "resolution_label": "temperature_70_to_74",
                "provenance_hash": "sha256:fixture_weather_mini_pack",
            }
        ],
        "source_review": [
            "Public forecast snapshots must come from source-policy-approved public endpoints or manual downloads.",
            "Prediction-market snapshots must be public/read-only; authenticated trading endpoints are forbidden.",
        ],
    }


def _cross_market_mini_pack(lane_id: str) -> dict[str, Any]:
    return {
        "lane_id": lane_id,
        "schema_version": "cross_market_equivalence_mini_pack_v1",
        "paper_only": True,
        "profit_claim_allowed": False,
        "required_data": [
            "market_metadata",
            "semantic_relation_mapping",
            "orderbook_snapshots",
            "fees_spreads_liquidity",
            "resolution_labels",
            "timestamps",
        ],
        "schema_fields": [
            "relation_id",
            "left_market_id",
            "right_market_id",
            "relation_type",
            "mapping_confidence",
            "left_best_bid",
            "left_best_ask",
            "right_best_bid",
            "right_best_ask",
            "timestamp",
            "resolution_labels",
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
    }


def _crypto_spot_mini_pack(lane_id: str) -> dict[str, Any]:
    return {
        "lane_id": lane_id,
        "schema_version": "crypto_spot_mini_pack_v1",
        "paper_only": True,
        "profit_claim_allowed": False,
        "spot_only": True,
        "no_margin": True,
        "no_leverage": True,
        "no_futures_perps": True,
        "no_exchange_credentials": True,
        "no_order_placement": True,
        "required_data": [
            "public_candles",
            "public_orderbook_snapshots_if_available",
            "fees_spreads_slippage_assumptions",
            "timestamped_signals",
            "baselines",
            "placebos",
            "walk_forward_split",
        ],
        "schema_fields": [
            "symbol",
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "signal",
            "fee_bps",
            "spread_bps",
            "slippage_bps",
            "split_id",
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
    }


def _upgrade_blockers(guard: dict[str, Any]) -> list[str]:
    blockers = list(guard.get("blockers", []))
    blockers.extend(
        [
            "real_public_source_capture_required",
            "minimum_sample_requirement_not_met",
            "walk_forward_oos_required",
        ]
    )
    return sorted(set(blockers))


def _exact_next_commands(lane_id: str) -> list[str]:
    if lane_id == "pm_weather_forecast_market_mismatch":
        return [
            "python -m quant_os.cli research paper-profit-lane-tournament",
            "python -m quant_os.cli proving paper-profit-discovery-loop",
            "Prepare a source-policy-approved public weather and market snapshot bundle outside CI before re-running paper proving.",
        ]
    if lane_id.startswith("crypto_") or lane_id.startswith("btc_"):
        return [
            "python -m quant_os.cli proving paper-profit-discovery-loop",
            "Use public spot OHLCV only; keep exchange credentials absent.",
        ]
    return ["python -m quant_os.cli proving paper-profit-discovery-loop"]


def _first_rejected(evaluated: list[dict[str, Any]]) -> dict[str, Any]:
    if evaluated:
        return evaluated[0]
    return {
        "lane_id": "NO_TESTABLE_LANE_FOUND",
        "status": "REJECTED",
        "paper_profit_status": "NO_TESTABLE_LANE_FOUND",
        "status_reason": "No lanes evaluated.",
    }


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_discovery_loop.json"
    md_path = root / "latest_discovery_loop.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Paper-Profit Discovery Loop",
        "",
        "Bounded paper-only discovery loop. No execution authority and no profit claim.",
        "",
        f"Discovery status: {payload['discovery_status']}",
        f"Paper profit status: {payload['paper_profit_status']}",
        f"Selected lane: {payload['selected_lane_id']}",
        f"Stop reason: {payload['stop_reason']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Evaluated Lanes",
    ]
    lines.extend(
        "- {lane_id}: {paper_status} / {status}".format(
            lane_id=lane["lane_id"],
            paper_status=lane["paper_profit_status"],
            status=lane["status"],
        )
        for lane in payload["evaluated_lanes"]
    )
    lines.extend(["", "## Selected Lane Upgrade Blockers"])
    lines.extend(f"- {item}" for item in payload["selected_lane"].get("upgrade_blockers", []))
    lines.extend(["", "## Exact Next Commands"])
    lines.extend(f"- `{item}`" for item in payload["selected_lane"].get("exact_next_commands", []))
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
