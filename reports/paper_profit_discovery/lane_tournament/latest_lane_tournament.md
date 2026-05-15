# Paper-Profit Lane Tournament

Deterministic path-to-proof ranking. No profit claim and no execution authority.

Status: LANE_TOURNAMENT_COMPLETE
Selected lane: pm_weather_forecast_market_mismatch
Selected lane status: PROMOTE_TO_DATA_CAPTURE
Selected lane score: 127
Execution authority: NONE

## Ranked Lanes
- pm_weather_forecast_market_mismatch: PROMOTE_TO_DATA_CAPTURE (score 127) - Clean public-data shape and strong replay design, but real public snapshots are not present in repo yet.
- btc_eth_relative_strength_rotation: PROMOTE_TO_PAPER_TEST (score 123) - Clean spot-only replay, but probably lower structural edge.
- btc_range_breakout_with_cost_filter: PROMOTE_TO_PAPER_TEST (score 123) - Replayable but likely crowded.
- crypto_spot_momentum_reversion_intraday: PROMOTE_TO_PAPER_TEST (score 120) - Strong replayability, but edge risk is crowded and cost sensitive.
- crypto_volatility_regime_signal: PROMOTE_TO_PAPER_TEST (score 120) - Good diagnostic lane, but likely a filter rather than standalone edge.
- crypto_stat_arb_pairs: PROMOTE_TO_PAPER_TEST (score 112) - Replayable as long-only rotation, not true short stat arb.
- pm_market_bucket_boundary_mispricing: PROMOTE_TO_DATA_CAPTURE (score 107) - Testable after curated public bucket/rule capture.
- pm_cross_market_equivalence_arbitrage: PROMOTE_TO_DATA_CAPTURE (score 97) - Testable if relation mapping is curated and source-policy approved.
- pm_resolution_rule_mispricing: DEPRIORITIZED (score 67) - Source path exists, but semantic ambiguity makes first evidence slow.
- pm_crypto_updown_repricing_lag_revival: DEPRIORITIZED (score 66) - Prior real-cached evidence and allowed-intent gates failed.
- pm_event_timing_underreaction: DEPRIORITIZED (score 64) - Event feeds are source-specific and risk social-post shortcuts.
- funding_basis_arbitrage: RESEARCH_ONLY (score 36) - Requires futures/perps, leverage, or margin under current doctrine.
- crypto_spot_mean_reversion_after_liquidation_news_proxy: BLOCKED_SOURCE_UNAVAILABLE (score 28) - No approved public non-auth proxy is present.
- pm_lp_refresh_lag_arbitrage: BLOCKED_SOURCE_UNAVAILABLE (score 26) - Public maker/taker and maker-wallet/order attribution are missing.
- crypto_triangular_arbitrage_research_only: RESEARCH_ONLY (score 25) - Cost/fill realism is too weak without execution authority.
- crypto_cross_exchange_spot_arbitrage_research_only: RESEARCH_ONLY (score 24) - Too latency-sensitive and crowded for promotion under current doctrine.
- options_volatility_arbitrage: RESEARCH_ONLY (score 19) - Options are forbidden under current doctrine.
- uniswap_v3_lp_strategy: BLOCKED_EXECUTION_UNSAFE (score 13) - Requires wallets and on-chain position management.
- defi_cex_dex_arbitrage: BLOCKED_EXECUTION_UNSAFE (score 1) - Requires wallets and gas-sensitive on-chain execution.
- copy_trader_wallet_following_strategies: BLOCKED_EXECUTION_UNSAFE (score -10) - Copy trading and wallet mirroring are forbidden.

## Ranking Rules
- Rank deterministic path-to-proof, not expected profit.
- Never promote lanes with auth, wallet, order, cancellation, copy-trade, leverage, margin, futures, options, or source-unavailable blockers.
- Prefer public data, replayability, baselines, placebos, cost/fill realism, and low source ambiguity.
