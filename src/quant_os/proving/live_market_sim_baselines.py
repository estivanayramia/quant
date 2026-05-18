from __future__ import annotations

from typing import Any


def build_live_market_sim_baseline_comparison(
    *, strategy_net_pnl: float, baseline_pnls: dict[str, float] | None = None
) -> dict[str, Any]:
    baseline_pnls = baseline_pnls or {
        "no_trade": 0.0,
        "buy_at_market_naive": 0.0,
        "random_eligible_bucket": -0.05,
        "market_implied_probability": 0.0,
        "always_buy_nearest_bucket": -0.05,
    }
    best = max(baseline_pnls.values()) if baseline_pnls else 0.0
    beaten = strategy_net_pnl > best
    return {
        "status": "LIVE_SIM_BASELINES_BEATEN" if beaten else "LIVE_SIM_BASELINE_NOT_BEATEN",
        "baseline_beaten": beaten,
        "baseline_pnls": baseline_pnls,
        "best_baseline_pnl": best,
    }
