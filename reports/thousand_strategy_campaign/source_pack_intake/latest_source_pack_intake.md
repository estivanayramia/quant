# Source Pack Intake

Source packs are hypothesis inputs only; no proof status changed.
Status: SOURCE_PACK_INTAKE_READY
Primary files read: 176
Accepted ideas: 8
Deferred ideas: 1
Rejected ideas: 2
Money-worthy readiness remains: MONEY_WORTHY_BLOCKED_BY_OVERFIT
- ACCEPT: prediction_market_read_only_clob_replay (SOURCE_BACKED_PUBLIC_REPLAY_LANE) -> offline schema fixture plus freshness, stale-book, and resolved-label checks
- ACCEPT: replay_realism_veto_layer (REPLAY_REALISM_BEFORE_EDGE) -> stale book, adverse selection, partial-fill, spread, and latency stress fixtures
- ACCEPT: crypto_public_data_quality_filtered_momentum (CRYPTO_DATA_PROVENANCE_TIGHTENING) -> Kraken/Binance-compatible replay with stricter data provenance and cost stress
- ACCEPT: source_quality_filtering_and_evidence_pack (SOURCE_QUALITY_BEFORE_VARIANT_EXPANSION) -> compact evidence-card fixture with hashes and explicit proof/non-proof labels
- ACCEPT: calibration_holdout_walk_forward_protocol (MULTIPLE_TESTING_AND_CALIBRATION_HARDENING) -> holdout/walk-forward fixture that blocks neighboring-parameter fragility
- ACCEPT: prediction_market_structural_consistency_checks (STRUCTURAL_EDGE_REQUIRES_LOCKED_PUBLIC_REPLAY) -> fixture that proves basket/negation mispricing is net of spread and settlement risk
- ACCEPT: dependency_license_security_gate (NO_DEPENDENCY_ADOPTION_WITHOUT_REVIEW) -> dependency intake card blocks adoption until source/license/security review passes
- ACCEPT: source_backed_no_trade_veto_behavior (FEWER_HIGHER_QUALITY_TRADES) -> candidate is blocked when expected edge is smaller than replay uncertainty
- DEFER: weather_forecast_market_calibration (NEEDS_PUBLIC_OUTCOME_ALIGNMENT) -> single-city fixture with issue-time forecast alignment and resolved outcome labels
- REJECT: copy_trading_wallet_mirroring (UNSAFE_COPY_TRADING_REJECTED) -> none; unsafe execution logic rejected
- REJECT: stealth_scraping_or_anti_bot_collection (STEALTH_TOOLING_REJECTED) -> none; stealth collection rejected
Priority repo leads:
- REFERENCE_PUBLIC_DATA_ONLY: binance/binance-public-data -> crypto_public_forward_spot
- REFERENCE_PUBLIC_DATA_ONLY: ccxt/ccxt -> crypto_public_forward_spot
- REFERENCE_DRY_RUN_ONLY: freqtrade/freq -> crypto_public_forward_spot
- REFERENCE_READ_ONLY_FIRST: Polymarket/py-clob-client-v2 -> prediction_market_read_only_clob
- REFERENCE_PUBLIC_DATA_ONLY: warproxxx/poly_data -> prediction_market_read_only_clob
- REFERENCE_REPLAY_ARCHITECTURE_ONLY: evan-kolberg/prediction-market-backtesting -> prediction_market_read_only_clob
- REFERENCE_ARCHITECTURE_ONLY: nautechsystems/nautilus_trader -> event_driven_replay_architecture
- REFERENCE_BENCHMARK_ONLY: PolyBench/PolyBench -> prediction_market_read_only_clob
- DEFER_UNTIL_OUTCOME_ALIGNMENT: yangyuan-zhen/PolyWeather -> weather_issue_time_calibration
- ARCHIVE_FAILURE_MODES_ONLY: TopTrenDev/polymarket-kalshi-arbitrage-bot -> prediction_market_cross_platform_structure
