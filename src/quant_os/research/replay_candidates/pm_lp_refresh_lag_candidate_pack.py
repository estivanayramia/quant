from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.research.replay_candidates.pm_lp_refresh_lag_schema import (
    ALIASES,
    CANDIDATE_ID,
    build_pm_lp_refresh_lag_replay_schema,
)
from quant_os.research.replay_candidates.pm_lp_refresh_lag_source_policy import (
    build_pm_lp_refresh_lag_source_policy,
)
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/sequence47/candidate_pack")
LANE_REGISTRY_REPORT_ROOT = Path("reports/sequence47/lane_registry")

REQUIRED_FUTURE_DATA = [
    "public CLOB/orderbook snapshots",
    "public trade/fill events if available",
    "quote refresh timestamps",
    "maker/order attribution if available from public data",
    "two-sided quoting behavior",
    "inter-trade intervals",
    "spread maintenance",
    "liquidity/reward-market metadata",
    "spot directional triggers",
    "taker burst detection",
    "resolution labels",
    "fill/no-fill realism",
]

HARD_GUARDRAILS = [
    "no copy trading",
    "no wallet mirroring",
    "no private wallet labeling as truth",
    "no live execution",
    "no authenticated APIs",
    "no order endpoints",
    "no claimed P&L as evidence",
    "no social-post-to-trade shortcut",
]

BASELINE_PLACEBO_REQUIREMENTS = [
    "market_midquote_holdout",
    "no_skill_no_trade_baseline",
    "randomized_refresh_lag_timestamp_placebo",
    "directional_trigger_sign_flip_placebo",
    "same_market_non_lag_window_placebo",
    "cost_adjusted_market_baseline",
]

FILL_COST_REALISM_REQUIREMENTS = [
    "queue_position_or_no_fill_model",
    "fees_spread_slippage_and_adverse_selection",
    "partial_fill_sensitivity",
    "quote_disappearance_before_fill_check",
    "latency_bucket_sensitivity",
]


def build_pm_lp_refresh_lag_candidate_pack() -> dict[str, Any]:
    source_policy = build_pm_lp_refresh_lag_source_policy()
    return {
        "schema_version": "pm_lp_refresh_lag_candidate_pack_v1",
        "sequence": "47",
        "candidate_id": CANDIDATE_ID,
        "aliases": ALIASES,
        "candidate_family": "prediction_market_lp_refresh_lag",
        "candidate_readiness_status": "CANDIDATE_PACK_READY_FOR_DATA_ACQUISITION",
        "hypothesis_status": "UNPROVEN_HYPOTHESIS_ONLY",
        "hypothesis": (
            "Treat as an unproven hypothesis: after an LP-style maker order is hit, "
            "the opposite-side quote may remain stale for a short public-data window; "
            "if a public directional trigger confirms fair value moved, that stale quote "
            "may be mispriced."
        ),
        "required_future_data": REQUIRED_FUTURE_DATA,
        "hard_guardrails": HARD_GUARDRAILS,
        "replay_schema": build_pm_lp_refresh_lag_replay_schema(),
        "source_policy_summary": {
            "public_read_only_only": source_policy["public_read_only_only"],
            "allowed_source_types": [
                item["source_type"] for item in source_policy["allowed_sources"]
            ],
            "blocked_source_types": [
                item["source_type"] for item in source_policy["blocked_sources"]
            ],
            "social_post_to_trade_shortcut_allowed": source_policy[
                "social_post_to_trade_shortcut_allowed"
            ],
        },
        "event_definitions": [
            "refresh_lag_window",
            "stale_opposite_side_quote_after_public_fill",
            "public_directional_trigger_confirmation",
            "taker_burst_context",
        ],
        "baseline_placebo_requirements": BASELINE_PLACEBO_REQUIREMENTS,
        "fill_cost_realism_requirements": FILL_COST_REALISM_REQUIREMENTS,
        "data_availability_blockers": [
            "PUBLIC_SOURCES_REQUIRED_NOT_ACQUIRED",
            "QUOTE_REFRESH_TIMESTAMPS_NOT_VERIFIED",
            "FILL_NO_FILL_REALISM_NOT_MODELED",
        ],
        "social_claim_policy": {
            "claimed_pnl_is_evidence": False,
            "wallet_lists_are_truth": False,
            "social_posts_can_seed_hypotheses": True,
            "copy_trade_advice_allowed": False,
        },
        "lane_registry_entry": build_pm_lp_refresh_lag_lane_registry(),
        "network_fetch_attempted": False,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def build_pm_lp_refresh_lag_lane_registry() -> dict[str, Any]:
    return {
        "schema_version": "pm_lp_refresh_lag_lane_registry_v1",
        "sequence": "47",
        "selected_candidate_id": CANDIDATE_ID,
        "aliases": ALIASES,
        "prior_candidate": {
            "candidate_id": "pm_crypto_updown_repricing_lag",
            "status": "DEPRIORITIZE_CANDIDATE",
            "reason": "allowed primary intents stayed 3 < 5 and allowed real-cached intents stayed 2 < 3",
        },
        "registry_status": "NEXT_REPLAY_CANDIDATE_SELECTED_FOR_DATA_DESIGN",
        "lane_scope": [
            "candidate pack",
            "data requirements",
            "replay schema",
            "public source policy",
            "fixture-safe tests",
        ],
        "explicitly_disabled": [
            "live trading",
            "order placement",
            "order cancellation",
            "wallet signing",
            "copy trading",
            "wallet mirroring",
        ],
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_pm_lp_refresh_lag_candidate_pack_report(
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    payload = build_pm_lp_refresh_lag_candidate_pack()
    payload["report_paths"] = _write_candidate_pack_report(payload, output_root=output_root)
    registry = payload["lane_registry_entry"]
    registry["report_paths"] = _write_lane_registry_report(registry, output_root=output_root)
    payload["lane_registry_entry"] = registry
    return payload


def _write_candidate_pack_report(
    payload: dict[str, Any],
    *,
    output_root: str | Path,
) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_candidate_pack.json"
    md_path = root / "latest_candidate_pack.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 47 PM LP Refresh-Lag Candidate Pack",
        "",
        "Research-only candidate pack. No live execution, wallet signing, order routing, order placement, or cancellation.",
        "",
        f"Status: {payload['candidate_readiness_status']}",
        f"Candidate: {payload['candidate_id']}",
        f"Hypothesis status: {payload['hypothesis_status']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        "",
        "## Required Future Data",
    ]
    lines.extend(f"- {item}" for item in payload["required_future_data"])
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in payload["hard_guardrails"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def _write_lane_registry_report(
    payload: dict[str, Any],
    *,
    output_root: str | Path,
) -> dict[str, str]:
    root = Path(output_root) / LANE_REGISTRY_REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_lane_registry.json"
    md_path = root / "latest_lane_registry.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 47 Lane Registry",
        "",
        "Next replay candidate lane registry. No execution authority.",
        "",
        f"Selected candidate: {payload['selected_candidate_id']}",
        f"Prior candidate status: {payload['prior_candidate']['status']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
