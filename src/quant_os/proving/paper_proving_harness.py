from __future__ import annotations

from itertools import accumulate
from statistics import mean
from typing import Any

from quant_os.proving.paper_proving_models import (
    BaselineRow,
    CostModel,
    FillModel,
    PaperIntent,
    PaperProvingInput,
    PaperSignalRow,
    PlaceboRow,
)
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REQUIRED_WARNINGS = [
    "PAPER_ONLY_NOT_LIVE",
    "SIMULATED_FILLS_NOT_REAL_FILLS",
    "BACKTEST_NOT_PROOF",
    "COST_MODEL_ASSUMPTION",
    "SOURCE_QUALITY_LIMITATION",
    "NO_LIVE_AUTHORITY",
]


def build_fixture_safe_paper_proving_input(*, lane_id: str) -> PaperProvingInput:
    if lane_id.startswith("crypto_") or lane_id.startswith("btc_"):
        return _crypto_spot_fixture_input(lane_id)
    return _weather_fixture_input(lane_id)


def _weather_fixture_input(lane_id: str) -> PaperProvingInput:
    return PaperProvingInput(
        lane_id=lane_id,
        source_quality="SYNTHETIC_FIXTURE_ONLY",
        source_dependencies=("public_manual_capture_design",),
        signals=(
            PaperSignalRow(
                timestamp="2026-05-01T12:00:00Z",
                signal="forecast_bucket_above_market_mid",
                strength=0.22,
                provenance="fixture_safe_weather_mini_pack",
            ),
            PaperSignalRow(
                timestamp="2026-05-02T12:00:00Z",
                signal="forecast_bucket_below_market_mid",
                strength=0.18,
                provenance="fixture_safe_weather_mini_pack",
            ),
            PaperSignalRow(
                timestamp="2026-05-03T12:00:00Z",
                signal="forecast_bucket_above_market_mid",
                strength=0.12,
                provenance="fixture_safe_weather_mini_pack",
            ),
        ),
        intents=(
            PaperIntent(
                timestamp="2026-05-01T12:01:00Z",
                side="BUY",
                entry_price=0.42,
                exit_price=0.54,
                quantity=10.0,
                time_in_market_minutes=180.0,
            ),
            PaperIntent(
                timestamp="2026-05-02T12:01:00Z",
                side="BUY",
                entry_price=0.57,
                exit_price=0.50,
                quantity=10.0,
                time_in_market_minutes=170.0,
            ),
            PaperIntent(
                timestamp="2026-05-03T12:01:00Z",
                side="BUY",
                entry_price=0.48,
                exit_price=0.53,
                quantity=10.0,
                time_in_market_minutes=160.0,
            ),
        ),
        cost_model=CostModel(
            fee_bps=10.0,
            slippage_bps=20.0,
            spread_bps=35.0,
            description="Fixture-only conservative spread, fee, and slippage assumption.",
        ),
        fill_model=FillModel(
            fill_probability=0.65,
            average_fill_fraction=0.75,
            description="Fixture-only conservative partial-fill assumption.",
        ),
        baselines=(
            BaselineRow(
                name="market_baseline",
                net_pnl=0.02,
                description="Hold market-implied bucket without forecast adjustment.",
            ),
            BaselineRow(
                name="forecast_baseline",
                net_pnl=0.03,
                description="Forecast direction without market-price mismatch filter.",
            ),
        ),
        placebos=(
            PlaceboRow(
                name="stale_forecast_placebo",
                net_pnl=0.01,
                description="Use stale forecast timestamp.",
            ),
            PlaceboRow(
                name="random_bucket_placebo",
                net_pnl=-0.02,
                description="Random bucket selection.",
            ),
            PlaceboRow(
                name="timestamp_shift_placebo",
                net_pnl=0.00,
                description="Shift signal timestamps away from market snapshots.",
            ),
        ),
        min_trades_required=30,
        oos_walk_forward_required=True,
        oos_walk_forward_status="MISSING",
        synthetic_only=True,
        trial_count=1,
        trial_count_warning_present=True,
    )


def _crypto_spot_fixture_input(lane_id: str) -> PaperProvingInput:
    return PaperProvingInput(
        lane_id=lane_id,
        source_quality="SYNTHETIC_FIXTURE_ONLY",
        source_dependencies=("public_spot_candle_design",),
        signals=(
            PaperSignalRow(
                timestamp="2026-05-01T00:00:00Z",
                signal="btc_eth_relative_strength_rotation",
                strength=0.08,
                provenance="fixture_safe_crypto_spot_shape",
            ),
            PaperSignalRow(
                timestamp="2026-05-02T00:00:00Z",
                signal="btc_eth_relative_strength_rotation",
                strength=0.05,
                provenance="fixture_safe_crypto_spot_shape",
            ),
            PaperSignalRow(
                timestamp="2026-05-03T00:00:00Z",
                signal="btc_eth_relative_strength_rotation",
                strength=0.03,
                provenance="fixture_safe_crypto_spot_shape",
            ),
        ),
        intents=(
            PaperIntent(
                timestamp="2026-05-01T00:05:00Z",
                side="BUY",
                entry_price=100.0,
                exit_price=100.8,
                quantity=0.02,
                time_in_market_minutes=1440.0,
            ),
            PaperIntent(
                timestamp="2026-05-02T00:05:00Z",
                side="BUY",
                entry_price=100.8,
                exit_price=100.3,
                quantity=0.02,
                time_in_market_minutes=1440.0,
            ),
            PaperIntent(
                timestamp="2026-05-03T00:05:00Z",
                side="BUY",
                entry_price=100.3,
                exit_price=100.9,
                quantity=0.02,
                time_in_market_minutes=1440.0,
            ),
        ),
        cost_model=CostModel(
            fee_bps=12.0,
            slippage_bps=15.0,
            spread_bps=8.0,
            description="Fixture-only crypto spot fee, spread, and slippage assumption.",
        ),
        fill_model=FillModel(
            fill_probability=0.9,
            average_fill_fraction=1.0,
            description="Fixture-only next-bar spot fill assumption.",
        ),
        baselines=(
            BaselineRow(
                name="buy_and_hold_baseline",
                net_pnl=0.01,
                description="Hold spot asset through the fixture window.",
            ),
            BaselineRow(
                name="cash_baseline",
                net_pnl=0.0,
                description="No-position cash baseline.",
            ),
        ),
        placebos=(
            PlaceboRow(
                name="random_timestamp_placebo",
                net_pnl=-0.01,
                description="Randomly shift signal timestamps.",
            ),
            PlaceboRow(
                name="sign_flip_placebo",
                net_pnl=-0.02,
                description="Flip the rotation signal sign.",
            ),
            PlaceboRow(
                name="volatility_regime_placebo",
                net_pnl=0.0,
                description="Shuffle volatility regime labels.",
            ),
        ),
        min_trades_required=50,
        oos_walk_forward_required=True,
        oos_walk_forward_status="MISSING",
        synthetic_only=True,
        trial_count=1,
        trial_count_warning_present=True,
    )


def run_paper_proving_harness(proving_input: PaperProvingInput) -> dict[str, Any]:
    trade_rows = _trade_rows(proving_input)
    gross = round(sum(row["gross_pnl"] for row in trade_rows), 8)
    net = round(sum(row["net_pnl_after_costs"] for row in trade_rows), 8)
    fill_adjusted = round(sum(row["fill_adjusted_pnl"] for row in trade_rows), 8)
    wins = [row["net_pnl_after_costs"] for row in trade_rows if row["net_pnl_after_costs"] > 0]
    losses = [row["net_pnl_after_costs"] for row in trade_rows if row["net_pnl_after_costs"] <= 0]
    baseline_comparison = _baseline_comparison(net, proving_input.baselines)
    placebo_comparison = _placebo_comparison(net, proving_input.placebos)
    trade_count = len(trade_rows)
    warnings = list(REQUIRED_WARNINGS)
    if trade_count < proving_input.min_trades_required:
        warnings.append("SAMPLE_TOO_THIN")
    readiness_status = _readiness_status(
        proving_input=proving_input,
        trade_count=trade_count,
        net=net,
        baseline_comparison=baseline_comparison,
        placebo_comparison=placebo_comparison,
    )
    return {
        "schema_version": "paper_proving_harness_v1",
        "lane_id": proving_input.lane_id,
        "source_quality": proving_input.source_quality,
        "source_dependencies": list(proving_input.source_dependencies),
        "input_summary": proving_input.to_report_dict(),
        "trade_rows": trade_rows,
        "gross_simulated_pnl": gross,
        "net_simulated_pnl_after_costs": net,
        "fill_adjusted_pnl": fill_adjusted,
        "hit_rate": round(len(wins) / trade_count, 6) if trade_count else 0.0,
        "average_win": round(mean(wins), 8) if wins else 0.0,
        "average_loss": round(mean(losses), 8) if losses else 0.0,
        "max_drawdown": _max_drawdown([row["net_pnl_after_costs"] for row in trade_rows]),
        "trade_count": trade_count,
        "turnover": round(sum(abs(row["notional"]) for row in trade_rows), 8),
        "exposure": round(max((abs(row["notional"]) for row in trade_rows), default=0.0), 8),
        "time_in_market_minutes": round(
            sum(row["time_in_market_minutes"] for row in trade_rows), 8
        ),
        "baseline_comparison": baseline_comparison,
        "placebo_comparison": placebo_comparison,
        "oos_walk_forward_required": proving_input.oos_walk_forward_required,
        "oos_walk_forward_status": proving_input.oos_walk_forward_status,
        "sample_warnings": [warning for warning in warnings if warning == "SAMPLE_TOO_THIN"],
        "confidence_status": "LOW_CONFIDENCE_DIAGNOSTIC_ONLY",
        "readiness_status": readiness_status,
        "warnings": warnings,
        "cost_model_present": proving_input.cost_model is not None,
        "fill_model_present": proving_input.fill_model is not None,
        "baseline_comparison_present": bool(proving_input.baselines),
        "placebo_comparison_present": bool(proving_input.placebos),
        "one_row_dominance": _one_row_dominance(trade_rows),
        "synthetic_only": proving_input.synthetic_only,
        "trial_count": proving_input.trial_count,
        "trial_count_warning_present": proving_input.trial_count_warning_present,
        "live_fills_assumed_equal_to_paper": proving_input.live_fills_assumed_equal_to_paper,
        "uses_copy_trade_or_wallet_mirroring": proving_input.uses_copy_trade_or_wallet_mirroring,
        "uses_leverage_futures_or_margin": proving_input.uses_leverage_futures_or_margin,
        "paper_only": True,
        "profitability_claimed": False,
        "evidence_only": True,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
    }


def _trade_rows(proving_input: PaperProvingInput) -> list[dict[str, Any]]:
    fill_fraction = 0.0 if proving_input.fill_model is None else proving_input.fill_model.effective_fill_fraction
    rows = []
    for intent in proving_input.intents:
        direction = 1.0 if intent.side.upper() == "BUY" else -1.0
        notional = intent.entry_price * intent.quantity
        gross = direction * (intent.exit_price - intent.entry_price) * intent.quantity
        cost = 0.0 if proving_input.cost_model is None else proving_input.cost_model.cost_for_notional(notional)
        net = gross - cost
        rows.append(
            {
                "timestamp": intent.timestamp,
                "side": intent.side,
                "entry_price": intent.entry_price,
                "exit_price": intent.exit_price,
                "quantity": intent.quantity,
                "notional": round(notional, 8),
                "gross_pnl": round(gross, 8),
                "cost": round(cost, 8),
                "net_pnl_after_costs": round(net, 8),
                "fill_adjusted_pnl": round(net * fill_fraction, 8),
                "time_in_market_minutes": intent.time_in_market_minutes,
            }
        )
    return rows


def _baseline_comparison(net: float, baselines: tuple[BaselineRow, ...]) -> dict[str, Any]:
    best = max((row.net_pnl for row in baselines), default=None)
    return {
        "baseline_count": len(baselines),
        "best_baseline_net_pnl": best,
        "beats_best_baseline": best is not None and net > best,
        "rows": [row.to_report_dict() for row in baselines],
    }


def _placebo_comparison(net: float, placebos: tuple[PlaceboRow, ...]) -> dict[str, Any]:
    best = max((row.net_pnl for row in placebos), default=None)
    return {
        "placebo_count": len(placebos),
        "best_placebo_net_pnl": best,
        "beats_best_placebo": best is not None and net > best,
        "rows": [row.to_report_dict() for row in placebos],
    }


def _readiness_status(
    *,
    proving_input: PaperProvingInput,
    trade_count: int,
    net: float,
    baseline_comparison: dict[str, Any],
    placebo_comparison: dict[str, Any],
) -> str:
    if proving_input.synthetic_only:
        return "PAPER_PROFIT_DIAGNOSTIC_ONLY"
    if trade_count < proving_input.min_trades_required:
        return "PAPER_PROFIT_BLOCKED_BY_SAMPLE"
    if not baseline_comparison["beats_best_baseline"]:
        return "PAPER_PROFIT_BLOCKED_BY_BASELINE"
    if not placebo_comparison["beats_best_placebo"]:
        return "PAPER_PROFIT_BLOCKED_BY_PLACEBO"
    if net <= 0:
        return "NO_PAPER_PROFIT_SIGNAL"
    if proving_input.oos_walk_forward_required and proving_input.oos_walk_forward_status != "PASSED":
        return "PAPER_PROFIT_DIAGNOSTIC_ONLY"
    return "PAPER_PROFIT_CANDIDATE"


def _max_drawdown(pnl_series: list[float]) -> float:
    equity = list(accumulate(pnl_series))
    peak = 0.0
    max_dd = 0.0
    for value in equity:
        peak = max(peak, value)
        max_dd = min(max_dd, value - peak)
    return round(max_dd, 8)


def _one_row_dominance(trade_rows: list[dict[str, Any]]) -> bool:
    abs_values = [abs(row["net_pnl_after_costs"]) for row in trade_rows]
    total = sum(abs_values)
    if total == 0:
        return False
    return max(abs_values) / total > 0.8
