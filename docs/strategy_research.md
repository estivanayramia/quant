# Strategy Research

Phase 7 upgrades QuantOS into a deterministic research lab for feature building, candidate strategy testing, ablation, walk-forward validation, regime checks, overfitting checks, and conservative leaderboard reporting.

This is research only. It does not claim profitability, does not place live orders, and does not promote any strategy to live.

## Commands

```bash
make features-build
make strategy-research
make strategy-ablation
make strategy-walk-forward
make strategy-regime-tests
make strategy-overfit-check
make strategy-leaderboard
make strategy-research-report
make phase7-smoke
```

## Candidate Strategies

- `baseline_momentum`
- `mean_reversion`
- `breakout`
- `smc_structure`
- `liquidity_sweep_reversal`
- `no_trade`
- `random_placebo`

Each candidate emits deterministic signals and routes simulated candidate orders through the existing risk firewall when backtested. Strategies do not call AI providers, broker SDKs, exchange SDKs, Telegram, or Freqtrade.

## Reports

Reports are written under `reports/strategy/`. They are disposable research artifacts, not source of truth. OMS/PMS state, risk decisions, and events remain authoritative.

## Promotion

Phase 7 may label strategies as research-only, shadow candidates, or dry-run candidates. Live readiness remains blocked as `TINY_LIVE_BLOCKED`.
