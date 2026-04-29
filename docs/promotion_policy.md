# Promotion Policy

Strategies cannot promote themselves. Optimizers cannot promote strategies. Promotion requires deterministic reports, out-of-sample evidence, placebo comparison, stress tests, risk review, quarantine review, and human approval.

Milestone 1 has no capital promotion. All runs are simulated.

Phase 5 promotion readiness is intentionally strict. Dry-run readiness may be reported only for local dry-run monitoring evidence when safety checks pass. Live promotion always remains `TINY_LIVE_BLOCKED` until a future explicit policy, multi-week evidence, exchange reconciliation, permission verification, and human approval gate exist.

Phase 6 can report trade-level reconciliation as unavailable, warning, pass, or fail. Even a passing dry-run trade-level reconciliation does not unlock live trading.

Phase 7 can label strategies as `RESEARCH_ONLY`, `SHADOW_CANDIDATE`, `DRY_RUN_CANDIDATE`, `REJECTED`, or `NOT_ENOUGH_EVIDENCE`. It cannot label any strategy live-ready. Overfitting checks, placebo comparison, ablation, walk-forward validation, regime testing, and human review remain required before any later dry-run promotion.

Phase 8 evidence scoring can label research evidence as insufficient through dry-run candidate quality. It still reports live promotion as `LIVE_BLOCKED`; synthetic data, even broad synthetic data, is not live-money evidence.

Phase 9 historical data ingestion can strengthen research evidence, but it does not unlock live trading. Historical evidence can support research, shadow, or dry-run review only; live promotion remains `LIVE_BLOCKED`.

Phase 10 proving mode can report `DRY_RUN_PROVEN` after repeated safe cycles, but this is not live readiness. Live promotion remains blocked until a future explicit human-approved live canary phase exists.
