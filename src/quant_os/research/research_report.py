from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_os.adapters.event_store_jsonl import JsonlEventStore
from quant_os.adapters.market_data_parquet import LocalParquetMarketData
from quant_os.data.demo_data import seed_demo_data
from quant_os.features.feature_report import write_feature_report
from quant_os.research.backtest import run_backtest
from quant_os.research.candidate_strategies import STRATEGY_SPECS

RESEARCH_STRATEGIES = [
    "baseline_momentum",
    "mean_reversion",
    "breakout",
    "smc_structure",
    "liquidity_sweep_reversal",
    "no_trade",
    "random_placebo",
]


def ensure_research_data(symbol: str = "SPY"):
    if not (Path("data/demo") / f"{symbol}.parquet").exists():
        seed_demo_data(event_store=JsonlEventStore())
    return LocalParquetMarketData().load(symbol)


def run_strategy_research(symbol: str = "SPY") -> dict[str, Any]:
    frame = ensure_research_data(symbol)
    event_store = JsonlEventStore()
    results = {}
    for strategy in RESEARCH_STRATEGIES:
        result = run_backtest(
            frame, strategy=strategy, event_store=event_store, strategy_id=strategy
        )
        results[strategy] = {
            "strategy_id": strategy,
            "name": STRATEGY_SPECS[strategy].name,
            "metrics": result.metrics,
            "risk_rejections": result.risk_rejections,
            "fills": len(result.fills),
            "live_promotion_status": "TINY_LIVE_BLOCKED",
        }
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "PASS",
        "symbol": symbol,
        "results": results,
        "live_trading_enabled": False,
        "live_promotion_status": "TINY_LIVE_BLOCKED",
    }
    _write_report("reports/strategy/research/latest_research.json", payload, "Strategy Research")
    return payload


def write_strategy_research_report() -> dict[str, Any]:
    feature_summary = write_feature_report()
    research = run_strategy_research()
    from quant_os.research.leaderboard import build_strategy_leaderboard
    from quant_os.research.overfit_checks import run_overfit_checks
    from quant_os.research.regime_tests import run_regime_tests
    from quant_os.research.strategy_ablation import run_strategy_ablation
    from quant_os.research.walk_forward import run_walk_forward_validation

    ablation = run_strategy_ablation()
    walk_forward = run_walk_forward_validation()
    regime = run_regime_tests()
    overfit = run_overfit_checks()
    leaderboard = build_strategy_leaderboard()
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "feature_build_summary": feature_summary,
        "strategy_list": RESEARCH_STRATEGIES,
        "tournament_metrics": research["results"],
        "ablation_summary": ablation,
        "walk_forward_summary": walk_forward,
        "regime_summary": regime,
        "overfit_warnings": overfit["warnings"],
        "leaderboard": leaderboard,
        "rejected_strategies": leaderboard["rejected_strategies"],
        "dry_run_candidates": leaderboard["dry_run_candidates"],
        "live_promotion_status": "TINY_LIVE_BLOCKED",
        "next_commands": [
            "make.cmd features-build",
            "make.cmd strategy-ablation",
            "make.cmd strategy-walk-forward",
            "make.cmd strategy-overfit-check",
            "make.cmd strategy-leaderboard",
        ],
    }
    root = Path("reports/strategy")
    root.mkdir(parents=True, exist_ok=True)
    (root / "latest_research_report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8"
    )
    lines = [
        "# Strategy Research Report",
        "",
        "Research only. No live trading. No profitability claim.",
        "",
        f"Strategies tested: {len(RESEARCH_STRATEGIES)}",
        f"Live promotion: {payload['live_promotion_status']}",
        f"Dry-run candidates: {payload['dry_run_candidates']}",
        f"Rejected strategies: {payload['rejected_strategies']}",
    ]
    (root / "latest_research_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


def _write_report(path: str, payload: dict[str, Any], title: str) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
    md = output.with_suffix(".md")
    md.write_text(
        f"# {title}\n\nResearch only. No live trading.\n\nStatus: {payload['status']}\n",
        encoding="utf-8",
    )
