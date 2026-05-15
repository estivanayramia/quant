from __future__ import annotations

from decimal import Decimal
from typing import Any

from quant_os.proving.paper_proving_models import (
    ALLOWED_READINESS_STATUSES,
    NO_PAPER_PROFIT_SIGNAL,
    PAPER_PROFIT_BLOCKED_BY_BASELINE,
    PAPER_PROFIT_BLOCKED_BY_COSTS,
    PAPER_PROFIT_BLOCKED_BY_FILLS,
    PAPER_PROFIT_BLOCKED_BY_PLACEBO,
    PAPER_PROFIT_BLOCKED_BY_SAMPLE,
    PAPER_PROFIT_DIAGNOSTIC_ONLY,
    PAPER_PROVING_READY_FOR_SELECTED_LANE,
    PAPER_PROVING_SAFETY,
    REQUIRED_WARNINGS,
    decimal_ratio,
    decimal_value,
    max_drawdown,
    render_decimal,
)

_MISSING = object()


def build_default_paper_proving_input(
    *,
    lane_id: str = "pm_weather_forecast_market_mismatch",
    source_quality: str = "synthetic_fixture_plumbing_only",
    cost_model: dict[str, Any] | None | object = _MISSING,
    fill_model: dict[str, Any] | None | object = _MISSING,
    baseline_rows: list[dict[str, Any]] | None | object = _MISSING,
    placebo_rows: list[dict[str, Any]] | None | object = _MISSING,
) -> dict[str, Any]:
    return {
        "schema_version": "paper_proving_input_v1",
        "sequence": "49",
        "lane_id": lane_id,
        "source_quality": source_quality,
        "source_quality_tier": "SYNTHETIC_ONLY"
        if "synthetic" in source_quality
        else "PUBLIC_REPLAY",
        "signal_rows": [
            {
                "signal_id": "weather_fixture_signal_001",
                "timestamp": "2026-05-15T12:00:00Z",
                "edge_bps": 900,
                "direction": "BUY",
                "source_quality": source_quality,
            }
        ],
        "market_rows": [
            {
                "market_id": "weather_fixture_market_001",
                "timestamp": "2026-05-15T12:00:00Z",
                "best_bid": 0.41,
                "best_ask": 0.43,
                "mid": 0.42,
                "spread": 0.02,
                "liquidity": 250.0,
                "resolution_value": 0.58,
            }
        ],
        "hypothetical_orders": [
            {
                "intent_id": "weather_fixture_intent_001",
                "timestamp": "2026-05-15T12:00:00Z",
                "side": "BUY",
                "quantity": 10.0,
                "entry_price": 0.43,
                "exit_price": 0.58,
            }
        ],
        "cost_model": (
            {"fee_bps": 8.0, "spread_bps": 20.0, "slippage_bps": 15.0}
            if cost_model is _MISSING
            else cost_model
        ),
        "fill_model": (
            {
                "assumption": "conservative_partial_fill",
                "fill_ratio": 0.5,
                "queue_model": "displayed_liquidity_partial_no_queue_priority",
            }
            if fill_model is _MISSING
            else fill_model
        ),
        "risk_policy": {
            "max_notional": 25.0,
            "paper_only": True,
            "allow_live_orders": False,
        },
        "baseline_rows": (
            [{"baseline_id": "market_mid_baseline", "net_pnl": 0.02}]
            if baseline_rows is _MISSING
            else baseline_rows
        ),
        "placebo_rows": (
            [{"placebo_id": "timestamp_shift_placebo", "net_pnl": -0.03}]
            if placebo_rows is _MISSING
            else placebo_rows
        ),
        "minimum_sample_size": 30,
        "walk_forward": {
            "required": True,
            "available": False,
            "status": "OOS_WALK_FORWARD_MISSING",
        },
        "multiple_comparison_warning": "single_predeclared_lane_default_fixture",
        "synthetic_rows_counted_as_profit_evidence": False,
    }


def run_paper_proving(payload: dict[str, Any]) -> dict[str, Any]:
    orders = list(payload.get("hypothetical_orders", []))
    cost_model = payload.get("cost_model")
    fill_model = payload.get("fill_model")
    costs_included = _costs_included(cost_model)
    fill_included = isinstance(fill_model, dict) and decimal_value(fill_model.get("fill_ratio")) > 0
    fill_ratio = decimal_value(fill_model.get("fill_ratio")) if fill_included else Decimal("0")
    trades = [
        _simulate_order(order, cost_model=cost_model, fill_ratio=fill_ratio)
        for order in orders
    ]
    gross = sum((trade["gross_pnl_decimal"] for trade in trades), Decimal("0"))
    net = sum((trade["net_pnl_decimal"] for trade in trades), Decimal("0"))
    wins = [trade["net_pnl_decimal"] for trade in trades if trade["net_pnl_decimal"] > 0]
    losses = [trade["net_pnl_decimal"] for trade in trades if trade["net_pnl_decimal"] < 0]
    turnover = sum((trade["notional_decimal"] for trade in trades), Decimal("0"))
    equity = []
    running = Decimal("10000")
    for trade in trades:
        running += trade["net_pnl_decimal"]
        equity.append(running)
    baseline = _comparison(payload.get("baseline_rows", []), net, "baseline")
    placebo = _comparison(payload.get("placebo_rows", []), net, "placebo")
    sample_warnings = []
    minimum_sample_size = int(payload.get("minimum_sample_size", 30))
    if len(trades) < minimum_sample_size:
        sample_warnings.append("SAMPLE_TOO_THIN")
    warnings = _dedupe([*REQUIRED_WARNINGS, *sample_warnings])
    oos_status = _oos_status(payload.get("walk_forward", {}))
    source_quality_tier = payload.get("source_quality_tier", "UNKNOWN")
    readiness_status = _readiness_status(
        net=net,
        costs_included=costs_included,
        fill_included=fill_included,
        baseline=baseline,
        placebo=placebo,
        source_quality_tier=str(source_quality_tier),
        sample_warnings=sample_warnings,
    )
    serializable_trades = [
        {
            key: render_decimal(value) if key.endswith("_decimal") else value
            for key, value in trade.items()
            if not key.endswith("_decimal")
        }
        for trade in trades
    ]
    return {
        "schema_version": "paper_proving_report_v1",
        "sequence": "49",
        "lane_id": payload.get("lane_id"),
        "source_quality": payload.get("source_quality"),
        "source_quality_tier": source_quality_tier,
        "readiness_status": readiness_status,
        "allowed_readiness_statuses": ALLOWED_READINESS_STATUSES,
        "gross_simulated_pnl": render_decimal(gross),
        "net_simulated_pnl_after_costs": render_decimal(net),
        "fill_adjusted_pnl": render_decimal(net),
        "hit_rate": decimal_ratio(Decimal(len(wins)), Decimal(len(trades))),
        "average_win": render_decimal(sum(wins, Decimal("0")) / Decimal(len(wins)))
        if wins
        else "0",
        "average_loss": render_decimal(sum(losses, Decimal("0")) / Decimal(len(losses)))
        if losses
        else "0",
        "max_drawdown": max_drawdown(equity),
        "trade_count": len(trades),
        "turnover": render_decimal(turnover),
        "exposure": render_decimal(turnover),
        "time_in_market_seconds": len(trades) * 60,
        "cost_model": cost_model,
        "costs_included": costs_included,
        "fill_model": fill_model,
        "fill_assumptions_included": fill_included,
        "risk_policy": payload.get("risk_policy", {}),
        "baseline_comparison": baseline,
        "placebo_comparison": placebo,
        "sample_warnings": sample_warnings,
        "oos_walk_forward_status": oos_status,
        "confidence_status": _confidence_status(readiness_status),
        "warnings": warnings,
        "simulated_trades": serializable_trades,
        "one_row_dominance": _one_row_dominance(trades, net),
        "no_lookahead": True,
        "baseline_rows_count": len(payload.get("baseline_rows", []) or []),
        "placebo_rows_count": len(payload.get("placebo_rows", []) or []),
        "profit_claim_made": False,
        "synthetic_rows_counted_as_profit_evidence": False,
        **PAPER_PROVING_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _simulate_order(
    order: dict[str, Any],
    *,
    cost_model: dict[str, Any] | None,
    fill_ratio: Decimal,
) -> dict[str, Any]:
    side = str(order.get("side", "BUY")).upper()
    quantity = decimal_value(order.get("quantity")) * fill_ratio
    entry = decimal_value(order.get("entry_price"))
    exit_price = decimal_value(order.get("exit_price"))
    gross = (entry - exit_price) * quantity if side == "SELL" else (exit_price - entry) * quantity
    notional = entry * quantity
    fee_bps = decimal_value((cost_model or {}).get("fee_bps"))
    spread_bps = decimal_value((cost_model or {}).get("spread_bps"))
    slippage_bps = decimal_value((cost_model or {}).get("slippage_bps"))
    costs = notional * (fee_bps + spread_bps + slippage_bps) / Decimal("10000")
    net = gross - costs
    return {
        "intent_id": order.get("intent_id"),
        "side": side,
        "filled_quantity": render_decimal(quantity),
        "entry_price": render_decimal(entry),
        "exit_price": render_decimal(exit_price),
        "gross_pnl": render_decimal(gross),
        "costs": render_decimal(costs),
        "net_pnl": render_decimal(net),
        "gross_pnl_decimal": gross,
        "net_pnl_decimal": net,
        "notional_decimal": notional,
    }


def _costs_included(cost_model: dict[str, Any] | None) -> bool:
    if not isinstance(cost_model, dict):
        return False
    return any(
        decimal_value(cost_model.get(key)) > 0
        for key in ("fee_bps", "spread_bps", "slippage_bps")
    )


def _comparison(rows: list[dict[str, Any]] | None, net: Decimal, label: str) -> dict[str, Any]:
    if not rows:
        return {"included": False, "comparison": "MISSING", f"{label}_net_pnl": "0"}
    row_net = sum((decimal_value(row.get("net_pnl")) for row in rows), Decimal("0"))
    return {
        "included": True,
        f"{label}_net_pnl": render_decimal(row_net),
        "paper_minus_comparison": render_decimal(net - row_net),
        "paper_beats_comparison": net > row_net,
    }


def _oos_status(walk_forward: dict[str, Any]) -> str:
    if walk_forward.get("available") is True:
        return "OOS_WALK_FORWARD_AVAILABLE"
    if walk_forward.get("required", True):
        return "OOS_WALK_FORWARD_MISSING"
    return "OOS_WALK_FORWARD_NOT_REQUIRED"


def _readiness_status(
    *,
    net: Decimal,
    costs_included: bool,
    fill_included: bool,
    baseline: dict[str, Any],
    placebo: dict[str, Any],
    source_quality_tier: str,
    sample_warnings: list[str],
) -> str:
    if not costs_included:
        return PAPER_PROFIT_BLOCKED_BY_COSTS
    if not fill_included:
        return PAPER_PROFIT_BLOCKED_BY_FILLS
    if not baseline["included"]:
        return PAPER_PROFIT_BLOCKED_BY_BASELINE
    if not placebo["included"]:
        return PAPER_PROFIT_BLOCKED_BY_PLACEBO
    if source_quality_tier == "SYNTHETIC_ONLY":
        return PAPER_PROFIT_DIAGNOSTIC_ONLY
    if "SAMPLE_TOO_THIN" in sample_warnings:
        return PAPER_PROFIT_BLOCKED_BY_SAMPLE
    if net <= 0:
        return NO_PAPER_PROFIT_SIGNAL
    if not baseline.get("paper_beats_comparison"):
        return PAPER_PROFIT_BLOCKED_BY_BASELINE
    if not placebo.get("paper_beats_comparison"):
        return PAPER_PROFIT_BLOCKED_BY_PLACEBO
    return PAPER_PROVING_READY_FOR_SELECTED_LANE


def _confidence_status(readiness_status: str) -> str:
    if readiness_status == PAPER_PROVING_READY_FOR_SELECTED_LANE:
        return "PAPER_EVIDENCE_READY_FOR_OPERATOR_REVIEW"
    if readiness_status == PAPER_PROFIT_DIAGNOSTIC_ONLY:
        return "DIAGNOSTIC_ONLY_NO_PROFIT_CLAIM"
    return "BLOCKED_NO_PROFIT_CLAIM"


def _one_row_dominance(trades: list[dict[str, Any]], net: Decimal) -> dict[str, Any]:
    if not trades or net == 0:
        return {"detected": False, "dominance_ratio": "0"}
    largest = max(abs(trade["net_pnl_decimal"]) for trade in trades)
    ratio = largest / abs(net) if net else Decimal("0")
    return {"detected": ratio >= Decimal("0.80"), "dominance_ratio": render_decimal(ratio)}


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped = []
    for item in items:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped
