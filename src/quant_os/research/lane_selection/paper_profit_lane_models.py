from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

LANE_STATUSES = [
    "PROMOTE_TO_PAPER_TEST",
    "PROMOTE_TO_DATA_CAPTURE",
    "RESEARCH_ONLY",
    "BLOCKED_SOURCE_UNAVAILABLE",
    "BLOCKED_EXECUTION_UNSAFE",
    "BLOCKED_COST_FILL_UNREALISTIC",
    "BLOCKED_TOO_CROWDED_OR_LATENCY_SENSITIVE",
    "DEPRIORITIZED",
    "REJECTED",
]

PROMOTABLE_STATUSES = {"PROMOTE_TO_PAPER_TEST", "PROMOTE_TO_DATA_CAPTURE"}


@dataclass(frozen=True)
class LaneScoreProfile:
    public_data_availability: int
    historical_depth: int
    timestamp_quality: int
    label_resolution_quality: int
    source_provenance: int
    replayability: int
    oos_walk_forward_feasibility: int
    frequency: int
    spread_liquidity: int
    fill_realism: int
    fee_slippage_resilience: int
    latency_resilience: int
    capacity_crowding_resilience: int
    execution_simplicity: int
    baseline_testability: int
    placebo_testability: int
    anti_overfit_feasibility: int
    calibration_feasibility: int
    minimum_sample_feasibility: int
    one_row_dominance_resilience: int
    no_auth_wallet_order_requirement: int
    no_leverage_futures_margin_requirement: int
    no_copy_trade_dependency: int
    no_social_post_shortcut: int
    repo_compatibility: int
    time_to_honest_paper_evidence: int

    def to_report_dict(self) -> dict[str, int]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class PaperProfitLane:
    lane_id: str
    family: str
    description: str
    score_profile: LaneScoreProfile
    data_requirements: tuple[str, ...]
    baselines: tuple[str, ...]
    placebos: tuple[str, ...]
    cost_model: str
    fill_model: str
    minimum_sample_requirement: str
    source_path: str
    status: str
    status_reason: str
    blockers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    research_only: bool = False
    mini_pack_type: str | None = None
    reviewed_sources: tuple[str, ...] = ()
    total_score: int = field(init=False)

    def __post_init__(self) -> None:
        if self.status not in LANE_STATUSES:
            raise ValueError(f"unknown lane status: {self.status}")
        object.__setattr__(self, "total_score", _score_total(self.score_profile, self.status))

    @property
    def promotable(self) -> bool:
        return self.status in PROMOTABLE_STATUSES and not self.research_only and not self.blockers

    def to_report_dict(self) -> dict[str, Any]:
        return {
            "lane_id": self.lane_id,
            "family": self.family,
            "description": self.description,
            "score_profile": self.score_profile.to_report_dict(),
            "total_score": self.total_score,
            "status": self.status,
            "status_reason": self.status_reason,
            "promotable": self.promotable,
            "research_only": self.research_only,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "data_requirements": list(self.data_requirements),
            "baselines": list(self.baselines),
            "placebos": list(self.placebos),
            "cost_model": self.cost_model,
            "fill_model": self.fill_model,
            "minimum_sample_requirement": self.minimum_sample_requirement,
            "source_path": self.source_path,
            "mini_pack_type": self.mini_pack_type,
            "reviewed_sources": list(self.reviewed_sources),
        }


def rank_paper_profit_lanes(lanes: list[PaperProfitLane] | None = None) -> list[PaperProfitLane]:
    candidates = lanes or build_default_lane_universe()
    return sorted(candidates, key=lambda lane: (-lane.total_score, lane.lane_id))


def build_default_lane_universe() -> list[PaperProfitLane]:
    return [
        _lane(
            lane_id="pm_weather_forecast_market_mismatch",
            family="prediction_market",
            description=(
                "Weather forecast bucket mismatch against prediction-market range contracts."
            ),
            scores=(5, 5, 5, 5, 5, 5, 5, 4, 4, 4, 5, 4, 4, 5, 5, 5, 5, 5, 4, 5, 5, 5, 5, 5, 5, 5),
            data_requirements=(
                "forecast_snapshots",
                "forecast_timestamp",
                "market_metadata",
                "bucket_range_rules",
                "market_price_snapshots",
                "liquidity_spread",
                "resolution_labels",
            ),
            baselines=("market_baseline", "forecast_baseline"),
            placebos=("stale_forecast_placebo", "random_bucket_placebo", "timestamp_shift_placebo"),
            cost_model="spread plus fee and slippage stress",
            fill_model="limit-taker conservative fill fraction with spread/liquidity stress",
            minimum_sample_requirement="at least 30 independent weather events before any claim",
            source_path="public weather APIs plus public prediction-market snapshots",
            status="PROMOTE_TO_DATA_CAPTURE",
            status_reason=(
                "Clean public-data shape and strong replay design, but real public snapshots are "
                "not present in repo yet."
            ),
            warnings=("manual_public_capture_required", "fixture_is_plumbing_only"),
            mini_pack_type="weather",
            reviewed_sources=(
                "https://www.weather.gov/documentation/services-web-api",
                "https://open-meteo.com/en/docs",
                "https://docs.polymarket.com/market-data/overview",
            ),
        ),
        _lane(
            lane_id="pm_cross_market_equivalence_arbitrage",
            family="prediction_market",
            description="Equivalent contracts across venues or semantically matched markets.",
            scores=(4, 3, 4, 4, 4, 3, 4, 3, 2, 2, 3, 3, 3, 2, 5, 5, 4, 3, 3, 4, 5, 5, 5, 5, 3, 3),
            data_requirements=(
                "market_metadata",
                "semantic_relation_mapping",
                "orderbook_snapshots",
                "fees_spreads_liquidity",
                "resolution_labels",
                "timestamps",
            ),
            baselines=("no_skill_baseline", "market_mid_baseline"),
            placebos=("random_relation_placebo", "stale_relation_placebo"),
            cost_model="two-venue spread, fee, partial-fill, and no-fill stress",
            fill_model="both-leg fill/no-fill and partial-fill model",
            minimum_sample_requirement="at least 20 relation groups across event types",
            source_path="public metadata and read-only orderbook snapshots",
            status="PROMOTE_TO_DATA_CAPTURE",
            status_reason="Testable if relation mapping is curated and source-policy approved.",
            warnings=("semantic_mapping_risk", "manual_relation_review_required"),
            mini_pack_type="cross_market",
            reviewed_sources=("https://docs.polymarket.com/market-data/overview",),
        ),
        _lane(
            lane_id="crypto_spot_momentum_reversion_intraday",
            family="crypto_spot",
            description="Spot-only intraday momentum/reversion with walk-forward cost filters.",
            scores=(5, 5, 5, 3, 5, 5, 5, 5, 3, 4, 3, 3, 3, 5, 5, 5, 4, 4, 5, 4, 5, 5, 5, 5, 5, 4),
            data_requirements=("public_candles", "fee_schedule_assumption", "spread_slippage_model"),
            baselines=("buy_and_hold_baseline", "no_skill_baseline"),
            placebos=("random_timestamp_placebo", "sign_flip_placebo", "volatility_regime_placebo"),
            cost_model="spot fee, spread, and slippage sensitivity",
            fill_model="public candle execution with conservative next-bar fill assumption",
            minimum_sample_requirement="at least 200 bars per walk-forward fold",
            source_path="public spot OHLCV only",
            status="PROMOTE_TO_PAPER_TEST",
            status_reason="Strong replayability, but edge risk is crowded and cost sensitive.",
            warnings=("crowding_risk", "cost_sensitivity_high"),
            mini_pack_type="crypto_spot",
            reviewed_sources=("https://github.com/binance/binance-public-data",),
        ),
        _lane(
            lane_id="crypto_stat_arb_pairs",
            family="crypto_spot",
            description="Spot-only pair spread diagnostics without shorting or leverage.",
            scores=(5, 5, 5, 3, 5, 4, 5, 4, 3, 3, 2, 3, 3, 4, 5, 5, 4, 4, 4, 4, 5, 5, 5, 5, 4, 3),
            data_requirements=("public_candles", "pair_universe", "transaction_cost_assumptions"),
            baselines=("buy_and_hold_baseline", "cash_baseline"),
            placebos=("pair_shuffle_placebo", "timestamp_shift_placebo"),
            cost_model="two-leg spot fee and slippage sensitivity",
            fill_model="long-only rotation fills; no live shorting assumed",
            minimum_sample_requirement="multiple pair folds with turnover cap",
            source_path="public spot OHLCV only",
            status="PROMOTE_TO_PAPER_TEST",
            status_reason="Replayable as long-only rotation, not true short stat arb.",
            warnings=("short_leg_not_live_executable", "cost_sensitivity_high"),
            mini_pack_type="crypto_spot",
            reviewed_sources=("https://github.com/binance/binance-public-data",),
        ),
        _lane(
            lane_id="pm_resolution_rule_mispricing",
            family="prediction_market",
            description="Mispricing around public resolution rules and ambiguous buckets.",
            scores=(4, 3, 3, 3, 4, 3, 3, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 3, 2, 3, 5, 5, 5, 5, 3, 3),
            data_requirements=("market_rules", "price_snapshots", "resolution_labels"),
            baselines=("market_mid_baseline",),
            placebos=("random_rule_placebo", "timestamp_shift_placebo"),
            cost_model="spread and fee sensitivity",
            fill_model="conservative no-fill and partial-fill variants",
            minimum_sample_requirement="many resolved markets with comparable rule text",
            source_path="public rules and resolved-market metadata",
            status="DEPRIORITIZED",
            status_reason="Source path exists, but semantic ambiguity makes first evidence slow.",
            warnings=("label_ambiguity_risk",),
        ),
        _lane(
            lane_id="pm_crypto_updown_repricing_lag_revival",
            family="prediction_market",
            description="Revisit crypto up/down repricing lag after prior allowed-intent failure.",
            scores=(3, 3, 4, 4, 4, 3, 3, 5, 2, 2, 2, 2, 2, 3, 4, 4, 3, 3, 2, 3, 5, 5, 5, 5, 3, 2),
            data_requirements=("real_cached_market_windows", "spot_snapshots", "allowed_intents"),
            baselines=("market_baseline", "no_intent_baseline"),
            placebos=("allowed_intent_shuffle", "spot_timestamp_shift"),
            cost_model="existing spread/fill stress from prior lane",
            fill_model="existing shadow policy only",
            minimum_sample_requirement="expanded real-cached evidence beyond prior failure",
            source_path="existing public/manual cache only",
            status="DEPRIORITIZED",
            status_reason="Prior real-cached evidence and allowed-intent gates failed.",
            blockers=("prior_allowed_intent_gate_failed",),
        ),
        _lane(
            lane_id="pm_lp_refresh_lag_arbitrage",
            family="prediction_market",
            description="LP refresh-lag arbitrage only if public attribution constraints disappear.",
            scores=(3, 2, 3, 4, 4, 2, 2, 4, 2, 1, 2, 1, 2, 2, 4, 4, 3, 2, 2, 2, 2, 5, 5, 5, 2, 1),
            data_requirements=("maker_taker_role", "maker_wallet_order_attribution", "orderbook_history"),
            baselines=("no_skill_baseline", "market_mid_baseline"),
            placebos=("stale_quote_placebo",),
            cost_model="maker/taker fee and adverse-selection stress",
            fill_model="requires public maker/taker and maker-order attribution",
            minimum_sample_requirement="publicly attributed fill sample",
            source_path="blocked by missing public fill attribution",
            status="BLOCKED_SOURCE_UNAVAILABLE",
            status_reason="Public maker/taker and maker-wallet/order attribution are missing.",
            blockers=("BLOCKED_MISSING_PUBLIC_FILL_ATTRIBUTION",),
            warnings=("prior_phase48_blocker_preserved",),
        ),
        _lane(
            lane_id="pm_event_timing_underreaction",
            family="prediction_market",
            description="Event timing underreaction using public event timestamps.",
            scores=(3, 3, 3, 4, 3, 3, 3, 3, 2, 2, 3, 2, 3, 3, 4, 4, 3, 3, 2, 3, 5, 5, 5, 4, 3, 3),
            data_requirements=("event_timestamps", "market_snapshots", "resolution_labels"),
            baselines=("market_baseline",),
            placebos=("event_timestamp_shift", "random_event_placebo"),
            cost_model="spread, fee, and event-latency stress",
            fill_model="late-arrival and no-fill model",
            minimum_sample_requirement="many independent event windows",
            source_path="public event feeds only if source-policy approved",
            status="DEPRIORITIZED",
            status_reason="Event feeds are source-specific and risk social-post shortcuts.",
            warnings=("source_policy_review_required",),
        ),
        _lane(
            lane_id="pm_market_bucket_boundary_mispricing",
            family="prediction_market",
            description="Bucket-boundary market pricing versus public reference values.",
            scores=(4, 3, 4, 4, 4, 4, 4, 3, 3, 3, 3, 4, 4, 4, 5, 5, 4, 4, 3, 4, 5, 5, 5, 5, 4, 4),
            data_requirements=("bucket_rules", "reference_values", "price_snapshots", "labels"),
            baselines=("market_baseline", "reference_value_baseline"),
            placebos=("random_bucket_placebo", "timestamp_shift_placebo"),
            cost_model="spread and liquidity stress near bucket boundaries",
            fill_model="conservative fill fraction and no-fill stress",
            minimum_sample_requirement="resolved boundary-adjacent market sample",
            source_path="public reference values and market snapshots",
            status="PROMOTE_TO_DATA_CAPTURE",
            status_reason="Testable after curated public bucket/rule capture.",
            warnings=("manual_rule_mapping_required",),
            mini_pack_type="weather",
        ),
        _lane(
            lane_id="crypto_volatility_regime_signal",
            family="crypto_spot",
            description="Spot-only volatility regime filter for existing signals.",
            scores=(5, 5, 5, 3, 5, 5, 5, 4, 3, 4, 3, 4, 3, 5, 5, 5, 4, 4, 5, 4, 5, 5, 5, 5, 5, 4),
            data_requirements=("public_candles", "volatility_features", "walk_forward_splits"),
            baselines=("buy_and_hold_baseline", "no_signal_baseline"),
            placebos=("volatility_regime_shuffle", "timestamp_shift_placebo"),
            cost_model="spot fee plus slippage sensitivity",
            fill_model="next-bar conservative public-candle fill",
            minimum_sample_requirement="multiple volatility regimes and OOS folds",
            source_path="public spot OHLCV only",
            status="PROMOTE_TO_PAPER_TEST",
            status_reason="Good diagnostic lane, but likely a filter rather than standalone edge.",
            warnings=("standalone_edge_uncertain",),
            mini_pack_type="crypto_spot",
        ),
        _lane(
            lane_id="crypto_cross_exchange_spot_arbitrage_research_only",
            family="crypto_spot",
            description="Cross-exchange spot arbitrage feasibility research only.",
            scores=(4, 3, 4, 2, 4, 2, 2, 5, 1, 1, 1, 1, 1, 1, 3, 3, 2, 2, 2, 2, 5, 5, 5, 5, 2, 1),
            data_requirements=("multi_exchange_books", "withdrawal_disabled", "fees", "latency"),
            baselines=("no_trade_baseline",),
            placebos=("exchange_shuffle_placebo",),
            cost_model="fee, spread, transfer, and latency stress",
            fill_model="requires simultaneous multi-venue fills; paper only",
            minimum_sample_requirement="orderbook archive across venues",
            source_path="public books may exist, but realistic execution is latency-sensitive",
            status="RESEARCH_ONLY",
            status_reason="Too latency-sensitive and crowded for promotion under current doctrine.",
            blockers=("latency_sensitive", "capacity_crowding_risk"),
            research_only=True,
        ),
        _lane(
            lane_id="crypto_triangular_arbitrage_research_only",
            family="crypto_spot",
            description="Triangular spot arbitrage feasibility research only.",
            scores=(4, 3, 5, 2, 4, 2, 2, 5, 1, 1, 1, 1, 1, 1, 3, 3, 2, 2, 2, 2, 5, 5, 5, 5, 2, 1),
            data_requirements=("exchange_orderbooks", "fees", "latency", "capacity"),
            baselines=("no_trade_baseline",),
            placebos=("symbol_shuffle_placebo",),
            cost_model="three-leg fee/spread/latency stress",
            fill_model="requires atomic or near-atomic fill assumptions",
            minimum_sample_requirement="deep orderbook archive",
            source_path="public books only; execution realism weak",
            status="RESEARCH_ONLY",
            status_reason="Cost/fill realism is too weak without execution authority.",
            blockers=("fill_realism_unavailable", "latency_sensitive"),
            research_only=True,
        ),
        _lane(
            lane_id="btc_eth_relative_strength_rotation",
            family="crypto_spot",
            description="Long-only BTC/ETH spot relative strength rotation.",
            scores=(5, 5, 5, 3, 5, 5, 5, 4, 4, 4, 4, 4, 3, 5, 5, 5, 4, 4, 5, 4, 5, 5, 5, 5, 5, 5),
            data_requirements=("public_candles", "fee_spread_slippage_assumptions"),
            baselines=("btc_buy_hold", "eth_buy_hold", "cash_baseline"),
            placebos=("timestamp_shift_placebo", "sign_flip_placebo"),
            cost_model="spot fee and turnover sensitivity",
            fill_model="next-bar conservative public-candle fill",
            minimum_sample_requirement="multiple market regimes and OOS folds",
            source_path="public spot OHLCV only",
            status="PROMOTE_TO_PAPER_TEST",
            status_reason="Clean spot-only replay, but probably lower structural edge.",
            warnings=("baseline_hard_to_beat",),
            mini_pack_type="crypto_spot",
        ),
        _lane(
            lane_id="btc_range_breakout_with_cost_filter",
            family="crypto_spot",
            description="BTC range breakout with explicit cost and slippage filter.",
            scores=(5, 5, 5, 3, 5, 5, 5, 4, 4, 4, 4, 4, 3, 5, 5, 5, 4, 4, 5, 4, 5, 5, 5, 5, 5, 5),
            data_requirements=("public_btc_candles", "spread_fee_assumptions", "walk_forward_splits"),
            baselines=("buy_and_hold_baseline", "cash_baseline"),
            placebos=("breakout_threshold_shuffle", "timestamp_shift_placebo"),
            cost_model="spot fee, spread, slippage, and turnover cap",
            fill_model="next-bar conservative public-candle fill",
            minimum_sample_requirement="multiple OOS folds",
            source_path="public spot OHLCV only",
            status="PROMOTE_TO_PAPER_TEST",
            status_reason="Replayable but likely crowded.",
            warnings=("crowded_signal_family",),
            mini_pack_type="crypto_spot",
        ),
        _lane(
            lane_id="crypto_spot_mean_reversion_after_liquidation_news_proxy",
            family="crypto_spot",
            description="Spot-only mean reversion after public liquidation/news proxy.",
            scores=(3, 3, 3, 2, 3, 2, 2, 3, 2, 3, 2, 2, 2, 4, 3, 3, 2, 2, 2, 3, 5, 5, 5, 3, 2, 2),
            data_requirements=("public_liquidation_proxy", "spot_candles", "source_policy_review"),
            baselines=("buy_and_hold_baseline", "no_news_baseline"),
            placebos=("news_timestamp_shift", "random_event_placebo"),
            cost_model="spot fee and event slippage stress",
            fill_model="next-bar conservative public-candle fill",
            minimum_sample_requirement="source-approved public proxy history",
            source_path="blocked unless public non-auth proxy is approved",
            status="BLOCKED_SOURCE_UNAVAILABLE",
            status_reason="No approved public non-auth proxy is present.",
            blockers=("public_non_auth_news_proxy_missing",),
        ),
        _lane(
            lane_id="defi_cex_dex_arbitrage",
            family="research_only",
            description="CEX/DEX arbitrage feasibility only.",
            scores=(2, 2, 2, 2, 2, 1, 1, 4, 1, 1, 1, 1, 1, 1, 2, 2, 1, 1, 1, 1, 1, 3, 5, 5, 1, 1),
            data_requirements=("wallet", "gas", "on_chain_execution", "cex_fills"),
            baselines=("no_trade_baseline",),
            placebos=("pool_shuffle_placebo",),
            cost_model="gas, MEV, fee, and latency stress",
            fill_model="requires wallets and gas-sensitive execution",
            minimum_sample_requirement="on-chain and CEX synchronized archive",
            source_path="unsafe for current doctrine",
            status="BLOCKED_EXECUTION_UNSAFE",
            status_reason="Requires wallets and gas-sensitive on-chain execution.",
            blockers=("wallet_required", "gas_sensitive_on_chain_execution"),
            research_only=True,
        ),
        _lane(
            lane_id="funding_basis_arbitrage",
            family="research_only",
            description="Funding/basis arbitrage feasibility only.",
            scores=(4, 4, 4, 2, 4, 3, 3, 4, 2, 2, 2, 2, 2, 2, 4, 4, 3, 3, 3, 3, 5, 1, 5, 5, 3, 2),
            data_requirements=("perps", "funding_rates", "margin", "basis_marks"),
            baselines=("cash_baseline",),
            placebos=("funding_timestamp_shift",),
            cost_model="funding, spread, fee, and liquidation risk",
            fill_model="requires perps/futures and margin assumptions",
            minimum_sample_requirement="multi-cycle funding sample",
            source_path="research only under no-futures doctrine",
            status="RESEARCH_ONLY",
            status_reason="Requires futures/perps, leverage, or margin under current doctrine.",
            blockers=("leverage_or_margin_or_futures_required",),
            research_only=True,
        ),
        _lane(
            lane_id="uniswap_v3_lp_strategy",
            family="research_only",
            description="Uniswap v3 LP strategy feasibility only.",
            scores=(3, 3, 3, 2, 3, 2, 2, 2, 1, 1, 1, 1, 1, 1, 3, 3, 2, 2, 2, 2, 1, 4, 5, 5, 2, 1),
            data_requirements=("wallet", "pool_state", "gas", "lp_positions"),
            baselines=("hodl_baseline",),
            placebos=("range_shuffle_placebo",),
            cost_model="gas, fee tier, impermanent loss, and MEV stress",
            fill_model="requires on-chain LP position management",
            minimum_sample_requirement="pool state archive",
            source_path="unsafe for current doctrine",
            status="BLOCKED_EXECUTION_UNSAFE",
            status_reason="Requires wallets and on-chain position management.",
            blockers=("wallet_required", "gas_sensitive_on_chain_execution"),
            research_only=True,
        ),
        _lane(
            lane_id="options_volatility_arbitrage",
            family="research_only",
            description="Options volatility arbitrage feasibility only.",
            scores=(3, 3, 3, 2, 3, 2, 2, 2, 1, 1, 1, 2, 1, 1, 4, 4, 3, 3, 2, 2, 5, 1, 5, 5, 2, 1),
            data_requirements=("options_chain", "vol_surface", "margin", "greeks"),
            baselines=("delta_hedged_baseline",),
            placebos=("vol_surface_shuffle",),
            cost_model="options spread, fee, and margin stress",
            fill_model="requires options execution and hedging assumptions",
            minimum_sample_requirement="large option-chain history",
            source_path="research only under no-options doctrine",
            status="RESEARCH_ONLY",
            status_reason="Options are forbidden under current doctrine.",
            blockers=("options_required", "leverage_or_margin_or_futures_required"),
            research_only=True,
        ),
        _lane(
            lane_id="copy_trader_wallet_following_strategies",
            family="research_only",
            description="Copy-trader and wallet-following strategies.",
            scores=(1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 5, 1, 5, 1, 1),
            data_requirements=("wallet_identity", "copy_trade_mapping", "private_attribution"),
            baselines=("no_trade_baseline",),
            placebos=("wallet_shuffle_placebo",),
            cost_model="not applicable; forbidden strategy family",
            fill_model="not applicable; forbidden strategy family",
            minimum_sample_requirement="not applicable",
            source_path="forbidden",
            status="BLOCKED_EXECUTION_UNSAFE",
            status_reason="Copy trading and wallet mirroring are forbidden.",
            blockers=("copy_trade_or_wallet_mirroring_forbidden",),
            research_only=True,
        ),
    ]


def _lane(
    *,
    lane_id: str,
    family: str,
    description: str,
    scores: tuple[int, ...],
    data_requirements: tuple[str, ...],
    baselines: tuple[str, ...],
    placebos: tuple[str, ...],
    cost_model: str,
    fill_model: str,
    minimum_sample_requirement: str,
    source_path: str,
    status: str,
    status_reason: str,
    blockers: tuple[str, ...] = (),
    warnings: tuple[str, ...] = (),
    research_only: bool = False,
    mini_pack_type: str | None = None,
    reviewed_sources: tuple[str, ...] = (),
) -> PaperProfitLane:
    return PaperProfitLane(
        lane_id=lane_id,
        family=family,
        description=description,
        score_profile=LaneScoreProfile(*scores),
        data_requirements=data_requirements,
        baselines=baselines,
        placebos=placebos,
        cost_model=cost_model,
        fill_model=fill_model,
        minimum_sample_requirement=minimum_sample_requirement,
        source_path=source_path,
        status=status,
        status_reason=status_reason,
        blockers=blockers,
        warnings=warnings,
        research_only=research_only,
        mini_pack_type=mini_pack_type,
        reviewed_sources=reviewed_sources,
    )


def _score_total(profile: LaneScoreProfile, status: str) -> int:
    raw = sum(profile.to_report_dict().values())
    if status == "PROMOTE_TO_PAPER_TEST":
        return raw + 5
    if status == "PROMOTE_TO_DATA_CAPTURE":
        return raw + 3
    if status == "DEPRIORITIZED":
        return raw - 20
    if status in {
        "RESEARCH_ONLY",
        "BLOCKED_SOURCE_UNAVAILABLE",
        "BLOCKED_EXECUTION_UNSAFE",
        "BLOCKED_COST_FILL_UNREALISTIC",
        "BLOCKED_TOO_CROWDED_OR_LATENCY_SENSITIVE",
    }:
        return raw - 45
    if status == "REJECTED":
        return raw - 80
    return raw
