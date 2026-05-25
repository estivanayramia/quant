from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.autonomy.live_market_sim_common import load_json, sim_safety_payload, write_state
from quant_os.proving.live_market_sim_baselines import build_live_market_sim_baseline_comparison
from quant_os.proving.live_market_sim_placebos import build_live_market_sim_placebo_comparison
from quant_os.readiness.canary_readiness_common import write_json_markdown_report

REPORT_DIR = Path("reports/live_market_sim_profitability/comparison")
MIN_UNIQUE_RESOLVED_MARKETS = 3
MAX_SINGLE_MARKET_RESOLVED_FILL_SHARE = 0.5


def build_live_market_sim_comparison(*, output_root: str | Path = ".") -> dict[str, Any]:
    pnl = load_json("reports/live_market_sim_profitability/pnl/latest_pnl.json", output_root=output_root) or {}
    raw_strategy = float(pnl.get("fake_net_pnl") or 0.0)
    strategy = float(pnl.get("proof_net_pnl", pnl.get("fake_net_pnl") or 0.0) or 0.0)
    unique_markets = int(pnl.get("proof_resolved_market_count", pnl.get("unique_resolved_market_count") or 0) or 0)
    concentration_share = float(
        pnl.get("proof_max_single_market_resolved_fill_share", pnl.get("max_single_market_resolved_fill_share") or 0.0)
        or 0.0
    )
    concentration_blockers = _concentration_blockers(
        unique_markets=unique_markets,
        concentration_share=concentration_share,
        resolved_count=int(pnl.get("resolved_outcome_count") or 0),
    )
    if pnl.get("status") != "LIVE_SIM_PNL_READY" or concentration_blockers:
        status = "LIVE_SIM_COMPARISON_PENDING"
        baseline = build_live_market_sim_baseline_comparison(strategy_net_pnl=strategy)
        placebo = build_live_market_sim_placebo_comparison(strategy_net_pnl=strategy)
    else:
        baseline = build_live_market_sim_baseline_comparison(strategy_net_pnl=strategy)
        placebo = build_live_market_sim_placebo_comparison(strategy_net_pnl=strategy)
        if not baseline["baseline_beaten"]:
            status = "LIVE_SIM_BASELINE_NOT_BEATEN"
        elif not placebo["placebo_beaten"]:
            status = "LIVE_SIM_PLACEBO_NOT_BEATEN"
        else:
            status = "LIVE_SIM_BASELINES_BEATEN"
    return sim_safety_payload(
        schema_version="live_market_sim_comparison_v1",
        status=status,
        allowed_statuses=[
            "LIVE_SIM_BASELINES_BEATEN",
            "LIVE_SIM_BASELINE_NOT_BEATEN",
            "LIVE_SIM_PLACEBO_NOT_BEATEN",
            "LIVE_SIM_COMPARISON_PENDING",
        ],
        strategy_net_pnl=strategy,
        raw_strategy_net_pnl=raw_strategy,
        proof_net_pnl=strategy,
        baseline_beaten=baseline["baseline_beaten"],
        placebo_beaten=placebo["placebo_beaten"],
        baseline_pnl=baseline["best_baseline_pnl"],
        placebo_pnl=placebo["best_placebo_pnl"],
        baseline=baseline,
        placebo=placebo,
        unique_resolved_market_count=unique_markets,
        unique_resolution_event_count=int(pnl.get("unique_resolution_event_count") or unique_markets),
        resolved_fill_count_by_market=pnl.get("resolved_fill_count_by_market") or {},
        proof_resolved_fill_count_by_market=pnl.get("proof_resolved_fill_count_by_market") or {},
        duplicate_resolved_fill_count_excluded_from_proof=pnl.get("duplicate_resolved_fill_count_excluded_from_proof")
        or 0,
        pnl_by_market=pnl.get("pnl_by_market") or {},
        max_single_market_resolved_fill_share=concentration_share,
        raw_max_single_market_resolved_fill_share=pnl.get("max_single_market_resolved_fill_share") or 0.0,
        concentration_guard={
            "min_unique_resolved_markets": MIN_UNIQUE_RESOLVED_MARKETS,
            "max_single_market_resolved_fill_share": MAX_SINGLE_MARKET_RESOLVED_FILL_SHARE,
            "passed": not concentration_blockers,
        },
        hit_rate=1.0 if strategy > 0 else 0.0,
        max_drawdown=min(strategy, 0.0),
        average_risk=0.24,
        blockers=[] if status == "LIVE_SIM_BASELINES_BEATEN" else list(dict.fromkeys([*concentration_blockers, status])),
        next_action="Run live simulated reconciliation.",
    )


def write_live_market_sim_comparison_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_live_market_sim_comparison(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_comparison.json",
        md_name="latest_comparison.md",
        title="Live Market Sim Comparison",
        summary="Baseline and placebo comparison for fake-money live-market simulated PnL.",
    )
    write_state(
        output_root=output_root,
        baseline_pnl=payload["baseline_pnl"],
        placebo_pnl=payload["placebo_pnl"],
        current_blockers=payload["blockers"],
        next_action=payload["next_action"],
    )
    return payload


def _concentration_blockers(
    *,
    unique_markets: int,
    concentration_share: float,
    resolved_count: int,
) -> list[str]:
    if resolved_count == 0:
        return []
    blockers: list[str] = []
    if unique_markets < MIN_UNIQUE_RESOLVED_MARKETS:
        blockers.append("MIN_UNIQUE_RESOLVED_MARKETS_NOT_MET")
    if concentration_share > MAX_SINGLE_MARKET_RESOLVED_FILL_SHARE:
        blockers.append("SINGLE_MARKET_RESOLUTION_CONCENTRATION")
    return blockers
