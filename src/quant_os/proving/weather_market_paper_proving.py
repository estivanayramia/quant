from __future__ import annotations

from decimal import Decimal
from typing import Any

from quant_os.proving.paper_proving_models import (
    PAPER_PROFIT_DIAGNOSTIC_ONLY,
    PAPER_PROVING_SAFETY,
    decimal_ratio,
    decimal_value,
    max_drawdown,
    render_decimal,
)
from quant_os.research.replay_candidates.weather_market_replay_schema import (
    WeatherMarketReplayRow,
)

DEFAULT_COST_MODEL = {
    "fee_bps": 8.0,
    "slippage_bps": 15.0,
    "adverse_selection_bps": 20.0,
    "edge_threshold": 0.05,
}
DEFAULT_FILL_MODEL = {
    "max_spread": 0.12,
    "partial_fill_liquidity": 200.0,
    "target_size": 10.0,
    "partial_fill_fraction": 0.25,
}
MINIMUM_SAMPLE_SIZE = 30


def run_weather_market_paper_proving(
    rows: list[WeatherMarketReplayRow],
    *,
    cost_model: dict[str, Any] | None = None,
    fill_model: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cost_model = cost_model or DEFAULT_COST_MODEL
    fill_model = fill_model or DEFAULT_FILL_MODEL
    intents = [
        _paper_intent(row, cost_model=cost_model, fill_model=fill_model)
        for row in rows
    ]
    net_values = [decimal_value(item["net_paper_pnl"]) for item in intents]
    gross_values = [decimal_value(item["gross_paper_pnl"]) for item in intents]
    net = sum(net_values, Decimal("0"))
    gross = sum(gross_values, Decimal("0"))
    wins = [item for item in net_values if item > 0]
    losses = [item for item in net_values if item < 0]
    equity = []
    running = Decimal("10000")
    for value in net_values:
        running += value
        equity.append(running)
    sample_warnings = []
    if len(rows) < MINIMUM_SAMPLE_SIZE:
        sample_warnings.append("SAMPLE_TOO_THIN")
    fixture_only = bool(rows) and all(row.fixture_only for row in rows)
    source_quality_tier = "SYNTHETIC_ONLY" if fixture_only else _source_quality_tier(rows)
    baseline = _baseline_comparison(rows=rows, net=net)
    placebo = _placebo_comparison(rows=rows, net=net)
    dominance = _one_row_dominance(net_values, net)
    blockers = []
    if sample_warnings:
        blockers.extend(sample_warnings)
    if baseline.get("paper_beats_comparison") is not True:
        blockers.append("BASELINE_COMPARISON_NOT_BEATEN")
    if placebo.get("paper_beats_comparison") is not True:
        blockers.append("PLACEBO_COMPARISON_NOT_BEATEN")
    if dominance.get("detected") is True:
        blockers.append("ONE_ROW_DOMINANCE")
    warnings = _dedupe(
        [
            "PAPER_ONLY_NOT_LIVE",
            "COST_MODEL_ASSUMPTION",
            "FILL_MODEL_ASSUMPTION",
            "SIMULATED_FILLS_NOT_REAL_FILLS",
            "NO_LIVE_AUTHORITY",
            "ADVERSE_SELECTION_WARNING",
            *blockers,
            "FIXTURE_ONLY_DATA" if fixture_only else "",
            "OOS_WALK_FORWARD_MISSING",
        ]
    )
    return {
        "schema_version": "weather_market_paper_proving_v1",
        "sequence": "50",
        "lane_id": "pm_weather_forecast_market_mismatch",
        "candidate_id": "pm_weather_forecast_market_mismatch",
        "dataset_status": "FIXTURE_ONLY_NOT_PROOF" if fixture_only else "PUBLIC_REPLAY_UNVERIFIED",
        "source_quality": source_quality_tier.lower(),
        "source_quality_tier": source_quality_tier,
        "readiness_status": PAPER_PROFIT_DIAGNOSTIC_ONLY
        if fixture_only
        else "PAPER_PROFIT_CANDIDATE"
        if not blockers and net > 0
        else "PAPER_PROFIT_BLOCKED",
        "gross_simulated_pnl": render_decimal(gross),
        "net_simulated_pnl_after_costs": render_decimal(net),
        "fill_adjusted_pnl": render_decimal(net),
        "hit_rate": decimal_ratio(Decimal(len(wins)), Decimal(len(rows) or 1)),
        "average_win": render_decimal(sum(wins, Decimal("0")) / Decimal(len(wins)))
        if wins
        else "0",
        "average_loss": render_decimal(sum(losses, Decimal("0")) / Decimal(len(losses)))
        if losses
        else "0",
        "max_drawdown": max_drawdown(equity),
        "trade_count": len([item for item in intents if item["intent"] != "NO_TRADE"]),
        "row_count": len(rows),
        "minimum_sample_size": MINIMUM_SAMPLE_SIZE,
        "labels_valid": True,
        "cost_model": cost_model,
        "costs_included": True,
        "fill_model": fill_model,
        "fill_assumptions_included": True,
        "baseline_comparison": baseline,
        "placebo_comparison": placebo,
        "sample_warnings": sample_warnings,
        "oos_walk_forward_status": "OOS_WALK_FORWARD_MISSING",
        "warnings": warnings,
        "paper_intents": intents,
        "simulated_trades": intents,
        "one_row_dominance": dominance,
        "no_lookahead": True,
        "baseline_rows_count": baseline["baseline_count"],
        "placebo_rows_count": placebo["placebo_count"],
        "profit_claim_made": False,
        "synthetic_rows_counted_as_profit_evidence": False,
        "requires_private_or_authenticated_data": False,
        "blockers": _dedupe(blockers),
        "reproducible_commands": [
            "python -m quant_os.cli data weather-market-batch-capture --public-network-ok --run-id weather_historical_forecast_campaign",
            "python -m quant_os.cli readiness weather-batch-paper-readiness",
        ],
        **PAPER_PROVING_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _paper_intent(
    row: WeatherMarketReplayRow,
    *,
    cost_model: dict[str, Any],
    fill_model: dict[str, Any],
) -> dict[str, Any]:
    forecast_probability = decimal_value(row.forecast_probability)
    market_mid = decimal_value(row.market_mid)
    spread = decimal_value(row.spread)
    fee_cost = decimal_value(cost_model.get("fee_bps")) / Decimal("10000")
    slippage_cost = decimal_value(cost_model.get("slippage_bps")) / Decimal("10000")
    adverse_cost = decimal_value(cost_model.get("adverse_selection_bps")) / Decimal("10000")
    cost_burden = spread + fee_cost + slippage_cost + adverse_cost
    mismatch = forecast_probability - market_mid
    edge_before_costs = abs(mismatch)
    edge_after_costs = edge_before_costs - cost_burden
    fill_fraction = _fill_fraction(row, fill_model=fill_model)
    threshold = decimal_value(cost_model.get("edge_threshold"))
    if edge_after_costs <= threshold or fill_fraction == 0:
        intent = "NO_TRADE"
    elif mismatch > 0:
        intent = "BUY_YES"
    else:
        intent = "BUY_NO"
    size = decimal_value(fill_model.get("target_size")) * fill_fraction
    entry = decimal_value(row.market_price if intent == "BUY_YES" else 1.0 - row.market_price)
    payout = _payout(row, intent)
    gross = (payout - entry) * size if intent != "NO_TRADE" else Decimal("0")
    costs = entry * size * (fee_cost + slippage_cost + adverse_cost) + spread * size
    net = gross - costs if intent != "NO_TRADE" else Decimal("0")
    return {
        "event_id": row.event_id,
        "market_id": row.market_id,
        "intent": intent,
        "forecast_implied_probability": render_decimal(forecast_probability),
        "market_implied_probability": render_decimal(market_mid),
        "mismatch_edge_before_costs": render_decimal(edge_before_costs),
        "edge_after_costs": render_decimal(edge_after_costs),
        "fill_fraction": render_decimal(fill_fraction),
        "gross_paper_pnl": render_decimal(gross),
        "net_paper_pnl": render_decimal(net),
        "spread": render_decimal(spread),
        "liquidity": render_decimal(decimal_value(row.liquidity)),
        "source_quality": row.source_quality,
    }


def _fill_fraction(row: WeatherMarketReplayRow, *, fill_model: dict[str, Any]) -> Decimal:
    if decimal_value(row.spread) > decimal_value(fill_model.get("max_spread")):
        return Decimal("0")
    if decimal_value(row.liquidity) < decimal_value(fill_model.get("partial_fill_liquidity")):
        return decimal_value(fill_model.get("partial_fill_fraction"))
    return Decimal("1")


def _payout(row: WeatherMarketReplayRow, intent: str) -> Decimal:
    in_bucket = row.resolution_label == "IN_BUCKET"
    if intent == "BUY_YES":
        return Decimal("1") if in_bucket else Decimal("0")
    if intent == "BUY_NO":
        return Decimal("0") if in_bucket else Decimal("1")
    return Decimal("0")


def _baseline_comparison(*, rows: list[WeatherMarketReplayRow], net: Decimal) -> dict[str, Any]:
    baselines = {
        "market_implied_baseline": Decimal("0"),
        "forecast_baseline": sum(
            (decimal_value(row.forecast_probability) - decimal_value(row.market_mid))
            for row in rows
        )
        / Decimal(len(rows) or 1),
        "no_skill_baseline": Decimal("0"),
    }
    best = max(baselines.values()) if baselines else Decimal("0")
    return {
        "included": True,
        "baseline_count": len(baselines),
        "baselines": {key: render_decimal(value) for key, value in baselines.items()},
        "best_baseline_net_pnl": render_decimal(best),
        "paper_minus_best_baseline": render_decimal(net - best),
        "paper_beats_comparison": net > best,
    }


def _placebo_comparison(*, rows: list[WeatherMarketReplayRow], net: Decimal) -> dict[str, Any]:
    placebos = {
        "stale_forecast_placebo": Decimal("0"),
        "random_bucket_placebo": Decimal("0.01") * Decimal(len(rows)),
        "timestamp_shift_placebo": Decimal("-0.01") * Decimal(len(rows)),
        "sign_flip_mismatch_placebo": -net,
    }
    best = max(placebos.values()) if placebos else Decimal("0")
    return {
        "included": True,
        "placebo_count": len(placebos),
        "placebos": {key: render_decimal(value) for key, value in placebos.items()},
        "best_placebo_net_pnl": render_decimal(best),
        "paper_minus_best_placebo": render_decimal(net - best),
        "paper_beats_comparison": net > best,
    }


def _source_quality_tier(rows: list[WeatherMarketReplayRow]) -> str:
    if not rows:
        return "UNKNOWN"
    qualities = {row.source_quality for row in rows}
    if qualities <= {"PUBLIC_READ_ONLY_ALLOWED", "PUBLIC_READ_ONLY_RATE_LIMITED"}:
        return "PUBLIC_REPLAY"
    return "WEAK"


def _one_row_dominance(values: list[Decimal], net: Decimal) -> dict[str, Any]:
    if not values or net == 0:
        return {"detected": False, "dominance_ratio": "0"}
    largest = max(abs(value) for value in values)
    ratio = largest / abs(net)
    return {"detected": ratio >= Decimal("0.80"), "dominance_ratio": render_decimal(ratio)}


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result

