from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.research.strategy_factory.campaign_common import (
    load_report,
    safe_payload,
    write_json_md,
)


def build_variant_public_forward_live_sim_summary(
    *,
    candidate: dict[str, Any] | None = None,
    observation_count: int = 0,
    eligible_intent_count: int = 0,
    completed_mark_count: int = 0,
    fake_net_pnl: float = 0.0,
) -> dict[str, Any]:
    candidate = candidate or {}
    return safe_payload(
        status="VARIANT_PUBLIC_FORWARD_LIVE_SIM_PENDING",
        selected_strategy_id=candidate.get("id"),
        selected_strategy_family=candidate.get("family"),
        selected_strategy_assets=candidate.get("assets", []),
        observation_count=observation_count,
        eligible_intent_count=eligible_intent_count,
        fake_fill_count=0,
        completed_mark_count=completed_mark_count,
        fake_net_pnl=round(fake_net_pnl, 8),
        data_sources=["kraken_public_rest_unauthenticated_forward_pending"],
        evidence_source="public_forward_live_sim_pending",
        public_forward_evidence_proven=False,
        public_unauthenticated_data_only=True,
        fake_money_only=True,
        no_credentials=True,
        no_orders=True,
        next_action="Collect candidate-matched public forward observations, intents, fills, and future marks.",
    )


def write_variant_public_forward_live_sim_summary(
    *,
    output_root: str | Path = ".",
    candidate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    tournament = load_report(
        output_root=output_root,
        report_dir="tournament",
        json_name="latest_tournament.json",
    )
    payload = build_variant_public_forward_live_sim_summary(
        candidate=candidate or tournament.get("current_best_candidate"),
    )
    return write_json_md(
        payload,
        output_root=output_root,
        report_dir="live_sim",
        json_name="latest_live_sim_summary.json",
        md_name="latest_live_sim_summary.md",
        title="Variant Public Forward Live Sim Summary",
        lines=[
            f"Status: {payload['status']}",
            f"Selected strategy: {payload['selected_strategy_id']}",
            f"Fake net PnL: {payload['fake_net_pnl']}",
            "No live orders, auth, credentials, or signing.",
        ],
    )
