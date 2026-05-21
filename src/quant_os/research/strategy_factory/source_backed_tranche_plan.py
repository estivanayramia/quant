from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.research.strategy_factory.campaign_common import (
    RESUME_COMMAND,
    load_report,
    safe_payload,
    write_campaign_state,
    write_json_md,
)


def build_source_backed_tranche_plan(
    *,
    intake: dict[str, Any] | None = None,
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    intake = intake or {}
    state = state or {}
    accepted = [idea for idea in intake.get("ideas", []) if idea.get("decision") == "ACCEPT"]
    deferred = [idea for idea in intake.get("ideas", []) if idea.get("decision") == "DEFER"]
    rejected = [idea for idea in intake.get("ideas", []) if idea.get("decision") == "REJECT"]

    families_added = [idea["strategy_family"] for idea in accepted]
    if not families_added:
        families_added = [
            "prediction_market_read_only_clob_replay",
            "replay_realism_veto_layer",
            "crypto_public_data_quality_filtered_momentum",
        ]
    families_deferred = [idea["strategy_family"] for idea in deferred]
    families_removed = sorted(
        {
            "copy_trading_wallet_mirroring",
            "stealth_scraping_or_anti_bot_collection",
            "coinflip_open_hour_bias",
            "final_seconds_resolution_gap",
            "unreviewed_public_bot_clone_strategy",
            *[idea["strategy_family"] for idea in rejected],
        }
    )
    blockers = list(state.get("blockers") or intake.get("existing_blockers_preserved") or [])
    blockers_addressed = sorted(
        {
            "PUBLIC_FORWARD_EVIDENCE_NOT_PROVEN",
            "OVERFIT_GUARD_NOT_PASSED",
            "REPEATABILITY_NOT_PASSED",
            "REPLAY_REALISM_STRESS_NOT_APPLIED",
            *blockers,
        }
    )

    return safe_payload(
        status="SOURCE_BACKED_TRANCHE_PLAN_READY",
        schema_version="source_backed_tranche_plan_v1",
        proof_status_changed=False,
        target_next_variants=360,
        live_public_market_priority_order=[
            "crypto_public_forward_spot",
            "prediction_market_read_only_clob",
            "event_driven_replay_architecture",
            "weather_issue_time_calibration",
        ],
        priority_repo_leads=list(intake.get("priority_repo_leads") or []),
        families_added=families_added,
        families_deferred=families_deferred,
        families_removed_or_deprioritized=families_removed,
        parameter_range_changes={
            "lookbacks": {"before": [5, 15, 30, 60, 120], "after": [5, 15, 30]},
            "holding_windows": {"before": [5, 15, 30, 60, 240], "after": [5, 15, 30]},
            "entry_z": {"before": [0.25, 0.5, 0.75, 1.0, 1.5], "after": [0.75, 1.0, 1.5]},
            "spread_cap_bps": {"before": [5.0, 10.0, 20.0], "after": [5.0, 10.0]},
            "liquidity_cap_usd": {"before": [1.0, 5.0, 25.0], "after": [1.0, 5.0]},
            "no_trade_edge_bps": {"change": "raise floor when execution uncertainty exceeds edge"},
        },
        required_public_data_paths=[
            {
                "name": "crypto_public_forward_spot",
                "markets": ["BTC/USD", "ETH/USD", "SOL/USD", "XRP/USD"],
                "required_fields": ["bid", "ask", "mid", "spread_bps", "timestamp", "future_mark"],
                "requires_auth": False,
                "changes_public_forward_collection": True,
            },
            {
                "name": "prediction_market_read_only_clob",
                "markets": ["Polymarket/Kalshi public CLOB markets"],
                "required_fields": [
                    "market_id",
                    "outcome",
                    "best_bid",
                    "best_ask",
                    "book_depth",
                    "trade_event",
                    "resolved_outcome",
                ],
                "requires_auth": False,
                "changes_public_forward_collection": True,
            },
            {
                "name": "weather_issue_time_calibration",
                "markets": ["temperature bucket markets"],
                "required_fields": ["forecast_issue_time", "bucket", "market_price", "resolved_temperature"],
                "requires_auth": False,
                "changes_public_forward_collection": False,
            },
        ],
        variants_should_be_generated_next=[
            {
                "family": "crypto_public_data_quality_filtered_momentum",
                "count": 120,
                "purpose": "continue current fast public-forward lane with tighter spread/liquidity/provenance filters",
            },
            {
                "family": "prediction_market_read_only_clob_replay",
                "count": 120,
                "purpose": "build replayable CLOB fixtures before any public-forward prediction-market sampling",
            },
            {
                "family": "replay_realism_veto_layer",
                "count": 80,
                "purpose": "stress candidates with stale book, latency, partial-fill, and adverse-selection vetoes",
            },
            {
                "family": "weather_forecast_market_calibration",
                "count": 40,
                "purpose": "deferred until issue-time forecasts and resolved outcomes are aligned",
            },
        ],
        variants_should_no_longer_be_generated=[
            "copy_trading_wallet_mirroring",
            "stealth_scraping_or_anti_bot_collection",
            "coinflip_open_hour_bias without venue-specific opening auction evidence",
            "final_seconds_resolution_gap without timestamp-latency and book-staleness proof",
            "wide spread cap variants where edge is below execution uncertainty",
        ],
        blockers_addressed=blockers_addressed,
        source_quality_filters=[
            "prefer official docs, maintained data repos, and reproducible fixtures",
            "reject PnL screenshots, popularity, stars, and social claims as evidence",
            "require license/source/security review before adopting dependencies",
        ],
        next_resume_command=RESUME_COMMAND,
    )


def write_source_backed_tranche_plan_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    intake = load_report(
        output_root=output_root,
        report_dir="source_pack_intake",
        json_name="latest_source_pack_intake.json",
    )
    state = load_report(output_root=output_root, report_dir="state", json_name="latest_state.json")
    payload = build_source_backed_tranche_plan(intake=intake, state=state)
    write_campaign_state(
        output_root=output_root,
        source_backed_tranche_plan_status=payload["status"],
        source_backed_target_next_variants=payload["target_next_variants"],
        source_backed_families_added=payload["families_added"],
        source_backed_families_removed_or_deprioritized=payload[
            "families_removed_or_deprioritized"
        ],
        blockers=payload["blockers_addressed"],
        next_action="Run the next tranche using the source-backed plan, then resume public-forward proof collection.",
        exact_resume_command=payload["next_resume_command"],
    )
    lines = [
        "This plan narrows future hypothesis generation; it does not promote any strategy.",
        f"Status: {payload['status']}",
        f"Target next variants: {payload['target_next_variants']}",
        f"Families added: {', '.join(payload['families_added'])}",
        f"Families removed/deprioritized: {', '.join(payload['families_removed_or_deprioritized'])}",
        f"Blockers addressed: {', '.join(payload['blockers_addressed'])}",
    ]
    lines.extend(
        f"- Generate {item['count']} {item['family']}: {item['purpose']}"
        for item in payload["variants_should_be_generated_next"]
    )
    return write_json_md(
        payload,
        output_root=output_root,
        report_dir="source_backed_tranche_plan",
        json_name="latest_source_backed_tranche_plan.json",
        md_name="latest_source_backed_tranche_plan.md",
        title="Source Backed Tranche Plan",
        lines=lines,
    )
