from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_os.research.backtest import run_backtest
from quant_os.research.research_report import ensure_research_data

ABLATION_VARIANTS = {
    "full_feature_set": "smc_structure",
    "no_smc_features": "breakout",
    "no_liquidity_features": "baseline_momentum",
    "no_session_features": "liquidity_sweep_reversal",
    "no_volatility_filter": "mean_reversion",
    "no_no_trade_filter": "baseline_momentum",
    "baseline_only": "baseline_momentum",
    "placebo": "random_placebo",
}


def run_strategy_ablation(symbol: str = "SPY") -> dict[str, Any]:
    frame = ensure_research_data(symbol)
    results: dict[str, Any] = {}
    for variant, strategy in ABLATION_VARIANTS.items():
        result = run_backtest(frame, strategy=strategy, strategy_id=f"ablation_{variant}")
        results[variant] = {
            "strategy": strategy,
            "metrics": result.metrics,
            "fills": len(result.fills),
            "risk_rejections": result.risk_rejections,
        }
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "PASS",
        "symbol": symbol,
        "results": results,
        "live_promotion_status": "TINY_LIVE_BLOCKED",
        "disclaimer": "Ablation is research only. No live trading.",
    }
    _write_ablation(payload)
    return payload


def _write_ablation(payload: dict[str, Any]) -> None:
    root = Path("reports/strategy/ablation")
    root.mkdir(parents=True, exist_ok=True)
    (root / "latest_ablation.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8"
    )
    lines = [
        "# Strategy Ablation",
        "",
        "Research only. No live trading. No profitability claim.",
        "",
        f"Status: {payload['status']}",
        "",
        "## Variants",
    ]
    for name, result in payload["results"].items():
        metrics = result["metrics"]
        lines.append(
            f"- {name}: strategy={result['strategy']} trades={metrics.get('number_of_trades', 0)} "
            f"return={metrics.get('total_return', 0.0):.6f}"
        )
    (root / "latest_ablation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
