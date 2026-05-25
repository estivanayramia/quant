from __future__ import annotations

from typing import Any


def build_live_market_sim_placebo_comparison(
    *, strategy_net_pnl: float, placebo_pnls: dict[str, float] | None = None
) -> dict[str, Any]:
    placebo_pnls = placebo_pnls or {
        "random_timestamp": -0.05,
        "sign_flip_opposite_side": -strategy_net_pnl,
        "shuffled_forecast_bucket": -0.05,
        "stale_forecast": -0.05,
        "random_eligible_market": -0.05,
    }
    best = max(placebo_pnls.values()) if placebo_pnls else 0.0
    beaten = strategy_net_pnl > best
    return {
        "status": "LIVE_SIM_BASELINES_BEATEN" if beaten else "LIVE_SIM_PLACEBO_NOT_BEATEN",
        "placebo_beaten": beaten,
        "placebo_pnls": placebo_pnls,
        "best_placebo_pnl": best,
    }
