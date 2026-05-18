from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.proving.thousand_strategy_capacity import build_thousand_strategy_capacity
from quant_os.proving.thousand_strategy_overfit_guard import build_thousand_strategy_overfit_guard
from quant_os.proving.thousand_strategy_repeatability import (
    write_thousand_strategy_repeatability_report,
)
from quant_os.readiness.money_worthy_strategy_readiness import (
    build_money_worthy_strategy_readiness,
)
from quant_os.research.strategy_factory.campaign_common import (
    load_report,
    write_campaign_state,
    write_json_md,
)
from quant_os.research.strategy_factory.strategy_tournament import run_strategy_tournament
from quant_os.risk.strategy_conflict_detector import write_strategy_conflict_detector_report


def write_money_worthy_strategy_readiness_report(
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    state = load_report(
        output_root=output_root,
        report_dir="state",
        json_name="latest_state.json",
    )
    batch_index = int(state.get("last_completed_batch_index", 1) or 1)
    persisted_tournament = load_report(
        output_root=output_root,
        report_dir="tournament",
        json_name="latest_tournament.json",
    )
    if (
        int(persisted_tournament.get("batch_index", 0) or 0) == batch_index
        and persisted_tournament.get("current_best_candidate")
    ):
        tournament = persisted_tournament
    else:
        tournament = run_strategy_tournament(batch_index=batch_index)
    overfit = build_thousand_strategy_overfit_guard()
    conflict = write_strategy_conflict_detector_report(
        output_root=output_root,
        candidate=_candidate_conflict_profile(tournament.get("current_best_candidate") or {}),
    )
    repeatability = write_thousand_strategy_repeatability_report(
        output_root=output_root,
        candidate=tournament.get("current_best_candidate"),
    )
    capacity = build_thousand_strategy_capacity()
    fresh_repro = load_report(
        output_root=output_root,
        report_dir="fresh_repro",
        json_name="latest_fresh_repro.json",
    ) or {"status": "FRESH_REPRO_BLOCKED"}
    payload = build_money_worthy_strategy_readiness(
        tournament=tournament,
        overfit=overfit,
        conflict=conflict,
        repeatability=repeatability,
        capacity=capacity,
        fresh_repro=fresh_repro,
    )
    write_campaign_state(
        output_root=output_root,
        campaign_status="THOUSAND_STRATEGY_CAMPAIGN_CHECKPOINTED_NOT_COMPLETE",
        money_worthy_readiness_status=payload["status"],
        manual_canary_packet_status="FIRST_TINY_MANUAL_CANARY_PACKET_BLOCKED",
        variants_generated=tournament.get("cumulative_variants_generated", tournament["variants_generated"]),
        variants_tested=tournament.get("cumulative_variants_tested", tournament["variants_tested"]),
        variants_rejected=tournament.get("cumulative_variants_rejected", tournament["variants_rejected"]),
        variants_promoted=0,
        current_best_candidate=payload["current_best_candidate"],
        blockers=payload["blockers"],
    )
    return write_json_md(
        payload,
        output_root=output_root,
        report_dir="final",
        json_name="latest_money_worthy_readiness.json",
        md_name="latest_money_worthy_readiness.md",
        title="Money-Worthy Strategy Readiness",
        lines=[f"Status: {payload['status']}", f"Blockers: {', '.join(payload['blockers'])}"],
    )


def _candidate_conflict_profile(candidate: dict[str, Any]) -> dict[str, Any]:
    configuration = candidate.get("variant_configuration") or {}
    thresholds = configuration.get("thresholds") or {}
    spread_cap_bps = float(configuration.get("spread_cap_bps", 10.0))
    fake_net_pnl = float(candidate.get("fake_net_pnl", 0.0))
    return {
        "selected_strategy_id": candidate.get("id"),
        "strategy_signal": "buy" if fake_net_pnl > 0 else "none",
        "regime_signal": "buy" if candidate.get("baseline_beaten") else "none",
        "liquidity_filter": "pass" if spread_cap_bps <= 10.0 else "fail",
        "edge_bps": max(fake_net_pnl, float(thresholds.get("no_trade_edge_bps", 0.0))),
        "execution_uncertainty_bps": spread_cap_bps,
        "source_fresh": bool(candidate.get("completed_marks", 0) and candidate.get("observations", 0)),
    }
