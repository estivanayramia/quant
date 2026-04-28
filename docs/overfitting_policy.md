# Overfitting Policy

QuantOS assumes strategy ideas are guilty until validation evidence says otherwise.

Phase 7 checks warn or block when:

- trade count is too low;
- a strategy only narrowly beats the random placebo;
- drawdown or fee/slippage stress is fragile;
- too many variants or parameters are being tested;
- train/test or walk-forward behavior is unstable;
- one regime or one symbol dominates the result.

The leaderboard uses a conservative score with penalties for drawdown, weak trade count, placebo weakness, and stress fragility. It is explicitly not sorted by total return alone.

No strategy can become live-ready in Phase 7.
