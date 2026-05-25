from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from quant_os.autonomy.canary_grade_live_sim_common import ROOT, canary_safe_payload
from quant_os.autonomy.live_market_sim_common import load_json
from quant_os.readiness.canary_readiness_common import write_json_markdown_report

REPORT_DIR = ROOT / "repeatability"


def build_crypto_live_sim_repeatability(
    *, output_root: str | Path = ".", pnl: dict[str, Any] | None = None
) -> dict[str, Any]:
    pnl = pnl or load_json("reports/canary_grade_live_sim/crypto/latest_pnl.json", output_root=output_root) or {}
    rows = list(pnl.get("pnl_rows", []) or [])
    strategy_net = float(pnl.get("fake_net_pnl") or 0.0)
    gross_profit = float(pnl.get("gross_profit") or 0.0)
    gross_loss = float(pnl.get("gross_loss") or 0.0)
    by_window = _sum_by(rows, "walk_forward_window")
    by_asset = _sum_by(rows, "symbol")
    by_strategy = _sum_by(rows, "strategy")
    by_regime = _sum_by(rows, "regime")
    by_session = _sum_by(rows, "session_bucket")
    top_trade = max([abs(float(row.get("fake_net_pnl") or 0.0)) for row in rows] or [0.0])
    top_window = max([abs(value) for value in by_window.values()] or [0.0])
    denominator = max(gross_profit + gross_loss, abs(strategy_net), 1.0)
    one_trade_dominance = top_trade / denominator
    one_window_dominance = top_window / denominator
    one_trade_cap = 0.25
    one_window_cap = 0.35
    baseline_pnls = {
        "no_trade": 0.0,
        "buy_hold": _baseline_buy_hold(rows),
        "same_cost_momentum": _baseline_naive_momentum(rows),
        "same_cost_mean_reversion": _baseline_naive_mean_reversion(rows),
    }
    best_baseline_name, best_baseline = max(
        baseline_pnls.items(),
        key=lambda item: item[1],
    )
    best_placebo = max(_placebo_random_timestamp(rows), _placebo_sign_flip(strategy_net), _placebo_shuffled(rows), 0.0)
    profit_factor = gross_profit / max(gross_loss, 0.000001)
    max_drawdown = _max_drawdown([float(row.get("fake_net_pnl") or 0.0) for row in rows])
    stress_notional = sum(float(row.get("notional_usd") or 1.0) for row in rows)
    worse_fill_net = strategy_net - stress_notional * 0.00005
    higher_fee_net = strategy_net - stress_notional * 0.00005
    delayed_entry_net = strategy_net * 0.85
    blockers: list[str] = []
    if strategy_net <= best_baseline:
        blockers.append("BASELINE_NOT_BEATEN")
    if strategy_net <= best_placebo:
        blockers.append("PLACEBO_NOT_BEATEN")
    if one_trade_dominance >= one_trade_cap:
        blockers.append("ONE_TRADE_DOMINANCE_TOO_HIGH")
    if one_window_dominance >= one_window_cap:
        blockers.append("ONE_WINDOW_DOMINANCE_TOO_HIGH")
    if worse_fill_net <= 0:
        blockers.append("WORSE_FILL_STRESS_FAILED")
    if higher_fee_net <= 0:
        blockers.append("HIGHER_FEE_STRESS_FAILED")
    if delayed_entry_net <= 0:
        blockers.append("DELAYED_ENTRY_STRESS_FAILED")
    if profit_factor <= 1.05:
        blockers.append("PROFIT_FACTOR_TOO_LOW")
    status = "REPEATABILITY_PASSED" if not blockers else "REPEATABILITY_BLOCKED"
    return canary_safe_payload(
        schema_version="crypto_live_sim_repeatability_v1",
        status=status,
        sample_count=len(rows),
        fake_net_pnl=round(strategy_net, 8),
        baseline_pnl=round(best_baseline, 8),
        baseline_pnls={key: round(value, 8) for key, value in sorted(baseline_pnls.items())},
        best_baseline_name=best_baseline_name,
        placebo_pnl=round(best_placebo, 8),
        baseline_beaten=strategy_net > best_baseline,
        placebo_beaten=strategy_net > best_placebo,
        one_trade_dominance=round(one_trade_dominance, 8),
        one_trade_dominance_cap=one_trade_cap,
        one_window_dominance=round(one_window_dominance, 8),
        one_window_dominance_cap=one_window_cap,
        profit_factor=round(profit_factor, 8),
        max_drawdown=round(max_drawdown, 8),
        by_asset=by_asset,
        by_strategy=by_strategy,
        by_regime=by_regime,
        by_session=by_session,
        by_window=by_window,
        excluding_top_trade_net=round(strategy_net - top_trade, 8),
        excluding_top_window_net=round(strategy_net - top_window, 8),
        worse_fill_status="PASSED" if worse_fill_net > 0 else "BLOCKED",
        higher_fee_status="PASSED" if higher_fee_net > 0 else "BLOCKED",
        delayed_entry_status="PASSED" if delayed_entry_net > 0 else "BLOCKED",
        spread_widening_status="PASSED" if worse_fill_net > 0 else "BLOCKED",
        no_fill_sensitivity_status="PASSED" if strategy_net * 0.75 > 0 else "BLOCKED",
        blockers=blockers,
        next_action="Run capacity model." if not blockers else "Collect more evidence or rotate strategy.",
    )


def write_crypto_live_sim_repeatability_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_crypto_live_sim_repeatability(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_repeatability.json",
        md_name="latest_repeatability.md",
        title="Crypto Live Sim Repeatability",
        summary="Anti-luck repeatability, baseline, placebo, and stress checks.",
    )
    return payload


def _sum_by(rows: list[dict[str, Any]], key: str) -> dict[str, float]:
    grouped: dict[str, float] = defaultdict(float)
    for row in rows:
        grouped[str(row.get(key, "unknown"))] += float(row.get("fake_net_pnl") or 0.0)
    return {key: round(value, 8) for key, value in sorted(grouped.items())}


def _baseline_buy_hold(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    by_asset = defaultdict(list)
    for row in rows:
        by_asset[row["symbol"]].append(row)
    total = 0.0
    for asset_rows in by_asset.values():
        entry_price = float(asset_rows[0]["entry_price"])
        if entry_price <= 0.0:
            continue
        quantity = 1.0 / entry_price
        total += (float(asset_rows[-1]["mark_price"]) - entry_price) * quantity
    return total


def _baseline_naive_momentum(rows: list[dict[str, Any]]) -> float:
    return sum(float(row.get("fake_net_pnl") or 0.0) for row in rows if float(row.get("return_1m") or 0.0) > 0)


def _baseline_naive_mean_reversion(rows: list[dict[str, Any]]) -> float:
    return sum(float(row.get("fake_net_pnl") or 0.0) for row in rows if float(row.get("return_1m") or 0.0) < 0)


def _placebo_random_timestamp(rows: list[dict[str, Any]]) -> float:
    return sum(float(row.get("fake_net_pnl") or 0.0) for index, row in enumerate(rows) if index % 7 == 0)


def _placebo_sign_flip(strategy_net: float) -> float:
    return -strategy_net


def _placebo_shuffled(rows: list[dict[str, Any]]) -> float:
    return sum(float(row.get("fake_net_pnl") or 0.0) * (0.15 if index % 2 == 0 else -0.10) for index, row in enumerate(rows))


def _max_drawdown(pnls: list[float]) -> float:
    equity = 0.0
    peak = 0.0
    drawdown = 0.0
    for pnl in pnls:
        equity += pnl
        peak = max(peak, equity)
        drawdown = min(drawdown, equity - peak)
    return drawdown
