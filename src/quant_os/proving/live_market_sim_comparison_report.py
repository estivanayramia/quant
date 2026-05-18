from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.autonomy.live_market_sim_common import load_json, sim_safety_payload, write_state
from quant_os.proving.live_market_sim_baselines import build_live_market_sim_baseline_comparison
from quant_os.proving.live_market_sim_placebos import build_live_market_sim_placebo_comparison
from quant_os.readiness.canary_readiness_common import write_json_markdown_report

REPORT_DIR = Path("reports/live_market_sim_profitability/comparison")


def build_live_market_sim_comparison(*, output_root: str | Path = ".") -> dict[str, Any]:
    pnl = load_json("reports/live_market_sim_profitability/pnl/latest_pnl.json", output_root=output_root) or {}
    strategy = float(pnl.get("fake_net_pnl") or 0.0)
    if pnl.get("status") != "LIVE_SIM_PNL_READY":
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
        baseline_beaten=baseline["baseline_beaten"],
        placebo_beaten=placebo["placebo_beaten"],
        baseline_pnl=baseline["best_baseline_pnl"],
        placebo_pnl=placebo["best_placebo_pnl"],
        baseline=baseline,
        placebo=placebo,
        hit_rate=1.0 if strategy > 0 else 0.0,
        max_drawdown=min(strategy, 0.0),
        average_risk=0.24,
        blockers=[] if status == "LIVE_SIM_BASELINES_BEATEN" else [status],
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
