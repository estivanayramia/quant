# Paper-Proving Diagnostic

Fixture-safe paper diagnostic. Backtests are not proof and fills are simulated.

Lane: pm_weather_forecast_market_mismatch
Readiness status: PAPER_PROFIT_DIAGNOSTIC_ONLY
Net simulated PnL after costs: 0.90445
Fill-adjusted PnL: 0.44091938
Trade count: 3
Execution authority: NONE

## Warnings
- PAPER_ONLY_NOT_LIVE
- SIMULATED_FILLS_NOT_REAL_FILLS
- BACKTEST_NOT_PROOF
- COST_MODEL_ASSUMPTION
- SOURCE_QUALITY_LIMITATION
- NO_LIVE_AUTHORITY
- SAMPLE_TOO_THIN

## Baselines
- market_baseline: 0.02
- forecast_baseline: 0.03

## Placebos
- stale_forecast_placebo: 0.01
- random_bucket_placebo: -0.02
- timestamp_shift_placebo: 0.0
