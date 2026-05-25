from __future__ import annotations

from copy import deepcopy
from typing import Any

PAPER_PROFIT_CANDIDATE_FOUND = "PAPER_PROFIT_CANDIDATE_FOUND"
CAMPAIGN_CHECKPOINTED_NOT_COMPLETE = "CAMPAIGN_CHECKPOINTED_NOT_COMPLETE"
CONTINUE_TO_NEXT_LANE = "CONTINUE_TO_NEXT_LANE"
EXPAND_SAFE_LANE_QUEUE = "EXPAND_SAFE_LANE_QUEUE"
NEEDS_FORWARD_DATA_CAPTURE = "NEEDS_FORWARD_DATA_CAPTURE"
NEEDS_HUMAN_APPROVAL = "NEEDS_HUMAN_APPROVAL"
TOOL_OR_CONTEXT_LIMIT_REACHED = "TOOL_OR_CONTEXT_LIMIT_REACHED"

FORBIDDEN_COMPLETION_STATUSES = [
    "NO_TESTABLE_EDGE_FOUND",
    "ALL_SAFE_LANES_EXHAUSTED",
    "NO_PROFIT_CLAIM_ALLOWED",
    "PAPER_PROFIT_DIAGNOSTIC_ONLY",
    "RESEARCH_ONLY",
    "BLOCKED_BY_SOURCE",
    "BLOCKED_BY_SAMPLE",
    "BLOCKED_BY_BASELINE",
    "BLOCKED_BY_PLACEBO",
    "BLOCKED_BY_COSTS",
    "BLOCKED_BY_FILLS",
]

CAMPAIGN_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
    "order_placement_enabled": False,
    "order_cancellation_enabled": False,
    "prediction_market_execution_authority_added": False,
    "browser_cookie_or_session_scraping_enabled": False,
    "paid_api_required": False,
    "evasion_enabled": False,
}


def build_initial_lane_universe() -> list[dict[str, Any]]:
    return [
        _pm(
            "pm_weather_forecast_market_mismatch",
            100,
            "Weather forecast probability versus prediction-market bucket price.",
            blocker_signature="HISTORICAL_FORECAST_SNAPSHOTS_MISSING",
            required_data=[
                "historical forecast snapshots issued before market close",
                "market/orderbook snapshots",
                "resolution labels",
            ],
        ),
        _pm(
            "pm_weather_historical_forecast_archive_mismatch",
            98,
            "Archived public forecast issue-time mismatch against weather markets.",
            blocker_signature="HISTORICAL_FORECAST_ARCHIVE_NOT_CAPTURED",
        ),
        _pm(
            "pm_weather_bucket_boundary_mispricing",
            96,
            "Adjacent weather bucket boundary inconsistencies.",
            blocker_signature="WEATHER_BUCKET_BOUNDARY_REPLAY_MISSING",
        ),
        _pm(
            "pm_cross_market_equivalence_arbitrage",
            89,
            "Equivalent public prediction-market contracts with inconsistent prices.",
            structural=True,
        ),
        _pm("pm_negation_pair_arbitrage", 88, "YES/NO or negation-pair probability bounds.", structural=True),
        _pm(
            "pm_mutually_exclusive_set_mispricing",
            87,
            "Mutually exclusive prediction-market outcome set sum bounds.",
            structural=True,
        ),
        _pm("pm_resolution_rule_mispricing", 70, "Resolution-rule misunderstanding lane.", structural=True),
        _pm("pm_event_timing_underreaction", 82, "Market underreaction after public event timing updates."),
        _pm("pm_market_bucket_boundary_mispricing", 80, "Generic bucket boundary inconsistency lane.", structural=True),
        _pm("pm_calendar_event_mispricing", 78, "Calendar event pricing mismatch lane."),
        _pm("pm_resolution_timing_delay_mispricing", 76, "Resolution timing delay repricing lane."),
        _pm("pm_news_vs_market_underreaction", 74, "Public news versus market underreaction lane."),
        _crypto("btc_eth_relative_strength_rotation", 73, "BTC/ETH spot relative strength rotation."),
        _crypto(
            "crypto_spot_momentum_reversion_intraday",
            72,
            "Spot-only intraday momentum or reversion.",
        ),
        _crypto("crypto_stat_arb_pairs", 71, "Spot-only pairs or cointegration-style paper lane."),
        _crypto("crypto_volatility_regime_signal", 70, "Spot-only volatility regime signal."),
        _crypto("btc_range_breakout_with_cost_filter", 69, "BTC range breakout with cost filter."),
        _crypto(
            "crypto_mean_reversion_after_extreme_move",
            68,
            "Spot-only mean reversion after extreme move.",
        ),
        _crypto("crypto_breakout_failure_reversion", 67, "Spot breakout failure reversion."),
        _crypto("crypto_session_volatility_pattern", 66, "Spot-only session volatility pattern."),
        _crypto("crypto_cross_asset_lead_lag_spot_only", 65, "Spot-only cross-asset lead lag."),
        _crypto("crypto_overnight_weekend_effect_spot_only", 64, "Spot-only overnight/weekend effect."),
        _crypto(
            "crypto_volatility_compression_breakout_spot_only",
            63,
            "Spot-only volatility compression breakout.",
        ),
        _equity("spy_qqq_relative_strength_rotation", 62, "SPY/QQQ paper-only relative strength."),
        _equity("sector_etf_momentum_rotation", 61, "Sector ETF paper-only momentum rotation."),
        _equity("equity_gap_reversion_paper_only", 60, "Equity gap reversion paper lane."),
        _equity("earnings_post_event_drift_paper_only", 59, "Earnings post-event drift paper lane."),
        _equity("index_volatility_regime_signal_paper_only", 58, "Index volatility regime paper lane."),
        _research("crypto_cross_exchange_spot_arbitrage", 40, "Cross-exchange spot arbitrage research lane."),
        _research("crypto_triangular_arbitrage", 39, "Triangular spot arbitrage research lane."),
        _research(
            "defi_cex_dex_arbitrage",
            20,
            "CEX/DEX arbitrage research lane.",
            requires_wallet_or_signing=True,
            on_chain_execution_risk=True,
        ),
        _research("funding_basis_arbitrage", 38, "Funding basis research lane.", requires_futures_or_margin=True),
        _research(
            "uniswap_v3_lp_strategy",
            19,
            "Uniswap v3 LP research lane.",
            requires_wallet_or_signing=True,
            on_chain_execution_risk=True,
        ),
        _research("options_volatility_arbitrage", 18, "Options volatility research lane.", requires_options=True),
        _research(
            "copy_trader_wallet_following",
            1,
            "Wallet-following research lane.",
            copy_trade_dependency=True,
            requires_wallet_or_signing=True,
        ),
    ]


def default_expansion_candidates() -> list[dict[str, Any]]:
    return [
        _equity(
            "macro_event_etf_reaction_paper_only",
            57,
            "Public macro-event reaction in SPY/QQQ/TLT/GLD paper-only replay.",
        ),
        _crypto(
            "crypto_spot_post_liquidation_reversion_proxy",
            56,
            "Spot-only public volatility shock reversion proxy without futures dependency.",
        ),
        _pm(
            "pm_public_fact_update_underreaction",
            55,
            "Prediction-market underreaction after timestamped public fact updates.",
        ),
        _pm(
            "pm_weather_nbm_vs_bucket_forward_capture",
            54,
            "Forward-captured NBM/NWS weather bucket mismatch with issue-time provenance.",
            blocker_signature="FORWARD_WEATHER_NBM_CAPTURE_NOT_STARTED",
        ),
        _crypto(
            "crypto_spot_intraday_seasonality_paper_only",
            53,
            "Spot-only intraday seasonality with public candles and no shorting.",
        ),
        _equity(
            "etf_month_turnaround_effect_paper_only",
            52,
            "Public ETF month-turnaround factor with SPY/QQQ benchmarks.",
        ),
        _equity(
            "public_macro_surprise_etf_drift_paper_only",
            51,
            "Public macro release drift in liquid ETFs using paper-only replay.",
        ),
        _pm(
            "pm_cross_platform_resolution_lag_public_only",
            50,
            "Publicly resolvable market timing lag where relation mapping is deterministic.",
            structural=True,
        ),
        _crypto(
            "crypto_spot_large_move_cooldown_reversion",
            49,
            "Spot-only reversion after large public candle moves with cost filters.",
        ),
        _crypto(
            "crypto_spot_liquidity_sweep_reversion_paper_only",
            48,
            "Spot-only reversion after public candle wick/liquidity-sweep proxies.",
        ),
        _crypto(
            "crypto_spot_volume_climax_reversion_paper_only",
            47,
            "Spot-only volume-climax reversion using public candles and conservative costs.",
        ),
        _equity(
            "liquid_etf_opening_range_reversal_paper_only",
            46,
            "Public liquid ETF opening-range reversal with benchmark and placebo replay.",
        ),
        _equity(
            "treasury_gold_risk_off_rotation_paper_only",
            45,
            "Public TLT/GLD/SPY risk-off rotation paper-only lane.",
        ),
        _pm(
            "pm_public_poll_release_underreaction",
            44,
            "Prediction-market underreaction after timestamped public poll releases.",
        ),
        _pm(
            "pm_public_filing_update_underreaction",
            43,
            "Prediction-market underreaction after timestamped public regulatory filings.",
        ),
        _pm(
            "pm_binary_bucket_monotonicity_check_public_only",
            42,
            "Public binary bucket monotonicity checks requiring deterministic relation mapping.",
            structural=True,
        ),
        _equity(
            "sector_etf_intraday_reversal_paper_only",
            41,
            "Public sector ETF intraday reversal paper-only lane with cost controls.",
        ),
        _crypto(
            "crypto_spot_asia_us_session_handoff_paper_only",
            40,
            "Spot-only Asia-to-US session handoff pattern using public candles.",
        ),
    ]


def lane_by_id(lane_id: str, lanes: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    for lane in lanes or build_initial_lane_universe():
        if lane["lane_id"] == lane_id:
            return deepcopy(lane)
    raise KeyError(f"Unknown relentless campaign lane: {lane_id}")


def _pm(
    lane_id: str,
    priority: int,
    description: str,
    *,
    structural: bool = False,
    blocker_signature: str | None = None,
    required_data: list[str] | None = None,
) -> dict[str, Any]:
    return _lane(
        lane_id,
        "prediction_market",
        priority,
        description,
        structural_relation_required=structural,
        blocker_signature=blocker_signature
        or ("VALIDATED_SEMANTIC_RELATION_MISSING" if structural else "PUBLIC_REPLAY_DATASET_MISSING"),
        required_data=required_data
        or ["market metadata", "orderbook snapshots", "resolution labels", "timestamped public source"],
    )


def _crypto(lane_id: str, priority: int, description: str) -> dict[str, Any]:
    return _lane(
        lane_id,
        "crypto_spot",
        priority,
        description,
        paper_only=True,
        spot_only=True,
        blocker_signature="PUBLIC_SPOT_REPLAY_DATASET_MISSING",
        required_data=[
            "public spot candles",
            "fee schedule",
            "spread/slippage assumptions",
            "walk-forward splits",
        ],
    )


def _equity(lane_id: str, priority: int, description: str) -> dict[str, Any]:
    return _lane(
        lane_id,
        "equity_etf_paper",
        priority,
        description,
        paper_only=True,
        blocker_signature="PUBLIC_EQUITY_REPLAY_DATASET_MISSING",
        required_data=["public OHLCV", "cost/slippage assumptions", "benchmark series"],
    )


def _research(
    lane_id: str,
    priority: int,
    description: str,
    *,
    requires_wallet_or_signing: bool = False,
    requires_futures_or_margin: bool = False,
    requires_options: bool = False,
    copy_trade_dependency: bool = False,
    on_chain_execution_risk: bool = False,
) -> dict[str, Any]:
    return _lane(
        lane_id,
        "research_only",
        priority,
        description,
        research_only=True,
        promotion_allowed=False,
        blocker_signature="RESEARCH_ONLY_LANE_CANNOT_PROMOTE",
        required_data=["document constraints only"],
        requires_wallet_or_signing=requires_wallet_or_signing,
        requires_futures_or_margin=requires_futures_or_margin,
        requires_options=requires_options,
        copy_trade_dependency=copy_trade_dependency,
        on_chain_execution_risk=on_chain_execution_risk,
    )


def _lane(
    lane_id: str,
    family: str,
    priority: int,
    description: str,
    *,
    required_data: list[str],
    blocker_signature: str,
    paper_only: bool = False,
    spot_only: bool = False,
    research_only: bool = False,
    promotion_allowed: bool = True,
    structural_relation_required: bool = False,
    requires_private_auth: bool = False,
    requires_wallet_or_signing: bool = False,
    requires_live_execution: bool = False,
    requires_paid_api: bool = False,
    requires_evasion: bool = False,
    requires_futures_or_margin: bool = False,
    requires_leverage: bool = False,
    requires_options: bool = False,
    requires_broker_credentials: bool = False,
    copy_trade_dependency: bool = False,
    on_chain_execution_risk: bool = False,
) -> dict[str, Any]:
    return {
        "lane_id": lane_id,
        "family": family,
        "description": description,
        "priority": priority,
        "public_data_available": not requires_private_auth,
        "replayable": not requires_live_execution,
        "timestamped": True,
        "baseline_testable": not research_only,
        "placebo_testable": not research_only,
        "cost_fill_model_possible": not on_chain_execution_risk,
        "required_data": required_data,
        "blocker_signature": blocker_signature,
        "paper_only": paper_only or family in {"prediction_market", "equity_etf_paper"},
        "spot_only": spot_only,
        "research_only": research_only,
        "promotion_allowed": promotion_allowed,
        "structural_relation_required": structural_relation_required,
        "allows_shorting": False,
        "requires_private_auth": requires_private_auth,
        "requires_wallet_or_signing": requires_wallet_or_signing,
        "requires_live_execution": requires_live_execution,
        "requires_paid_api": requires_paid_api,
        "requires_evasion": requires_evasion,
        "requires_futures_or_margin": requires_futures_or_margin,
        "requires_leverage": requires_leverage,
        "requires_options": requires_options,
        "requires_broker_credentials": requires_broker_credentials,
        "copy_trade_dependency": copy_trade_dependency,
        "on_chain_execution_risk": on_chain_execution_risk,
        "source_policy": "public_read_only_no_auth_no_paid_api",
        **CAMPAIGN_SAFETY,
    }
