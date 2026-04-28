from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_os.research.candidate_strategies import STRATEGY_SPECS
from quant_os.research.research_report import run_strategy_research


def run_overfit_checks(symbol: str = "SPY") -> dict[str, Any]:
    research = run_strategy_research(symbol)
    results = research["results"]
    warnings: list[str] = []
    blockers: list[str] = []
    placebo_return = float(results["random_placebo"]["metrics"].get("total_return", 0.0))
    best_strategy = None
    best_return = float("-inf")
    for strategy_id, result in results.items():
        metrics = result["metrics"]
        trade_count = int(metrics.get("number_of_trades", 0))
        total_return = float(metrics.get("total_return", 0.0))
        if total_return > best_return and strategy_id != "random_placebo":
            best_strategy = strategy_id
            best_return = total_return
        if trade_count < 20 and strategy_id not in {"no_trade"}:
            warnings.append(f"LOW_TRADE_COUNT:{strategy_id}")
        if STRATEGY_SPECS[strategy_id].parameter_count > 6:
            warnings.append(f"TOO_MANY_PARAMETERS:{strategy_id}")
        if float(metrics.get("max_drawdown", 0.0)) < -0.20:
            warnings.append(f"DRAWDOWN_STRESS:{strategy_id}")
    if best_strategy is None:
        blockers.append("NO_NON_PLACEBO_STRATEGY_TESTED")
    elif best_return - placebo_return < 0.01:
        warnings.append("PLACEBO_MARGIN_WEAK")
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "WARN" if warnings else "PASS",
        "best_strategy": best_strategy,
        "warnings": sorted(set(warnings)),
        "blockers": sorted(set(blockers)),
        "placebo_return": placebo_return,
        "best_non_placebo_return": best_return if best_strategy else None,
        "variant_count": len(results),
        "live_promotion_status": "TINY_LIVE_BLOCKED",
    }
    _write_overfit(payload)
    return payload


def _write_overfit(payload: dict[str, Any]) -> None:
    root = Path("reports/strategy/overfit")
    root.mkdir(parents=True, exist_ok=True)
    (root / "latest_overfit_check.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8"
    )
    lines = [
        "# Overfitting Checks",
        "",
        "Research only. No live trading. Warnings block automatic confidence.",
        "",
        f"Status: {payload['status']}",
        f"Best strategy: {payload['best_strategy']}",
        "",
        "## Warnings",
    ]
    lines.extend(f"- {warning}" for warning in (payload["warnings"] or ["None"]))
    (root / "latest_overfit_check.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
