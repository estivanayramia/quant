# Review Lenses

## P0/P1 Risks

- Any path that can place, cancel, resize, or authorize live orders outside deterministic gates.
- Any default config enabling live, leverage, futures, margin, shorts, withdrawals, keys, or command authority.
- Any kill-switch bypass.
- Any reconciliation mismatch ignored as safe.

## Research And Replay Risks

- Costs omitted from expectancy.
- Passive fills assumed without queue/latency skepticism.
- Placebo or no-trade baseline missing.
- Leakage in labels, splits, rolling features, or reference joins.
- Calibration outputs unbounded probabilities or constant optimistic sizes.

## Data And Validation Risks

- Stale, corrupt, duplicate, future, or missing data silently repaired.
- Missing explanation/reason code not failing validation.
- Reports implying live readiness.
- Tests requiring internet, Docker, keys, paid data, or real exchange APIs.
