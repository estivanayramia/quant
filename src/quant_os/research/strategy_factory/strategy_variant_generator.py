from __future__ import annotations

from itertools import product
from pathlib import Path
from typing import Any

from quant_os.research.strategy_factory.campaign_common import (
    PREREG_TS,
    SAFETY_STATE,
    safe_payload,
    stable_id,
    write_campaign_state,
    write_json_md,
)
from quant_os.research.strategy_factory.strategy_variant_models import StrategyVariant

FAMILIES = [
    "relative_strength_rotation",
    "momentum_reversion_intraday",
    "volatility_regime_momentum",
    "range_breakout_cost_filtered",
    "extreme_move_snapback",
    "breakout_failure_reversion",
    "volatility_compression_breakout",
    "cross_asset_lead_lag",
    "session_effect_filter",
    "liquidity_shock_reversion",
    "spread_normalization_signal",
    "volume_impulse_continuation",
    "volume_impulse_reversal",
    "trend_pullback_continuation",
    "moving_average_slope_filter",
    "realized_volatility_filter",
    "market_microstructure_no_trade_filter",
    "up_down_basket_arbitrage",
    "directional_arbitrage_with_hedge",
    "underlying_repricing_lag",
    "cross_timeframe_5m_15m_lag",
    "orderbook_imbalance_skew",
    "near_resolution_residual_yield",
    "coinflip_open_hour_bias",
    "final_seconds_resolution_gap",
    "fair_value_probability_lag",
    "nwp_bucket_probability_mismatch",
    "temperature_tail_mispricing",
    "temperature_ladder_relative_value",
    "multi_city_weather_forecast_mismatch",
    "forecast_distribution_vs_market_implied",
    "cross_platform_equivalence_spread",
    "negation_pair_mispricing",
    "mutually_exclusive_set_mispricing",
    "resolution_rule_mismatch",
    "settlement_timing_mismatch",
    "etf_relative_strength_rotation_public_only",
]

ASSETS = ["BTC/USD", "ETH/USD", "SOL/USD", "XRP/USD", "DOGE/USD", "BTC/ETH"]
LOOKBACKS = [5, 15, 30, 60, 120]
HOLDS = [5, 15, 30, 60, 240]
THRESHOLDS = [0.25, 0.5, 0.75, 1.0, 1.5]
SPREAD_CAPS = [5.0, 10.0, 20.0]
LIQUIDITY_CAPS = [1.0, 5.0, 25.0]


def generate_strategy_variants(
    *,
    target_count: int = 1000,
    batch_index: int = 1,
    families: list[str] | None = None,
    source_label: str = "pre_registered_public_strategy_factory_v1",
) -> list[StrategyVariant]:
    variants: list[StrategyVariant] = []
    seed = 630000 + ((batch_index - 1) * 1_000_000)
    selected_families = families or FAMILIES
    combinations = list(
        product(LOOKBACKS, HOLDS, THRESHOLDS, SPREAD_CAPS, LIQUIDITY_CAPS, selected_families)
    )
    for index in range(target_count):
        global_index = ((batch_index - 1) * target_count) + index
        universe_cycle = global_index // len(combinations)
        lookback, hold, threshold, spread_cap, liquidity_cap, family = combinations[global_index % len(combinations)]
        market_assets = _assets_for_family(family)
        seed += 1
        payload = {
            "family": family,
            "assets": market_assets,
            "lookback": lookback,
            "hold": hold,
            "threshold": threshold,
            "spread_cap": spread_cap,
            "liquidity_cap": liquidity_cap,
            "universe_cycle": universe_cycle,
            "seed": seed,
            "batch_index": batch_index,
        }
        variant: StrategyVariant = {
            "id": stable_id("tsv", payload, length=14),
            "batch_index": batch_index,
            "universe_cycle": universe_cycle,
            "family": family,
            "assets": market_assets,
            "source": source_label,
            "lookback": lookback,
            "holding_window": hold,
            "thresholds": {
                "entry_z": float(threshold),
                "no_trade_edge_bps": 2.0 + threshold + (universe_cycle * 0.05),
                "universe_cycle": float(universe_cycle),
            },
            "spread_cap_bps": float(spread_cap),
            "liquidity_cap_usd": float(liquidity_cap),
            "fee_model": {"fee_bps": 8.0, "spread_bps": spread_cap, "slippage_bps": 6.0},
            "fill_model": {"type": "conservative_no_guaranteed_fill", "max_fill_ratio": 0.5},
            "no_trade_conditions": [
                "edge_below_cost_uncertainty",
                "spread_above_cap",
                "stale_source",
                "conflict_detector_veto",
            ],
            "risk_cap": {"max_fake_notional_usd": 1.0, "max_position_fraction": 0.001},
            "expected_failure_modes": [
                "baseline_wins",
                "placebo_wins",
                "holdout_fails",
                "cost_stress_fails",
            ],
            "pre_registration_timestamp": PREREG_TS,
            "deterministic_seed": seed,
            "no_live_metadata": dict(SAFETY_STATE),
        }
        variants.append(variant)
    return variants


def write_strategy_variants_report(
    *,
    output_root: str | Path = ".",
    target_count: int = 1000,
    batch_index: int = 1,
    families: list[str] | None = None,
    source_label: str = "pre_registered_public_strategy_factory_v1",
    cumulative_variant_count: int | None = None,
    source_backed_plan_applied: bool = False,
) -> dict[str, Any]:
    variants = generate_strategy_variants(
        target_count=target_count,
        batch_index=batch_index,
        families=families,
        source_label=source_label,
    )
    total_variant_count = cumulative_variant_count or batch_index * len(variants)
    payload = safe_payload(
        status="STRATEGY_VARIANTS_PREREGISTERED",
        batch_index=batch_index,
        variant_count=len(variants),
        cumulative_variant_count=total_variant_count,
        variants=variants,
        top_k_preview=variants[:25],
        pre_registered_before_testing=True,
        deterministic_seed="strategy_factory_v1_seed_630000",
        family_count=len({variant["family"] for variant in variants}),
        asset_count=len({asset for variant in variants for asset in variant["assets"]}),
        source_backed_plan_applied=source_backed_plan_applied,
        source_backed_families=sorted(set(families or [])),
    )
    write_campaign_state(
        output_root=output_root,
        variants_generated=total_variant_count,
        last_completed_batch_index=batch_index,
        strategy_families_queued=sorted({variant["family"] for variant in variants}),
        source_backed_tranche_plan_status=(
            "SOURCE_BACKED_TRANCHE_PLAN_APPLIED" if source_backed_plan_applied else None
        ),
    )
    lines = [
        f"Status: {payload['status']}",
        f"Batch: {payload['batch_index']}",
        f"Variants: {payload['variant_count']}",
        f"Cumulative variants: {payload['cumulative_variant_count']}",
        f"Families: {payload['family_count']}",
        f"Assets: {payload['asset_count']}",
        "Pre-registered before testing: True",
    ]
    return write_json_md(
        payload,
        output_root=output_root,
        report_dir="variants",
        json_name="latest_strategy_variants.json",
        md_name="latest_strategy_variants.md",
        title="Strategy Variants",
        lines=lines,
    )


def _assets_for_family(family: str) -> list[str]:
    if "weather" in family or "temperature" in family:
        return ["KXHIGHNY", "KXHIGHLAX", "KXHIGHCHI"]
    if any(token in family for token in ["up_down", "prediction", "negation", "resolution"]):
        return ["BTC_UPDOWN_5M", "ETH_UPDOWN_15M", "SOL_UPDOWN_1H"]
    if "etf" in family:
        return ["SPY", "QQQ", "TLT", "GLD", "IWM"]
    return ASSETS[: 2 + (len(family) % 5)]
