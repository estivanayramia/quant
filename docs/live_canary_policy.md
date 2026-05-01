# Tiny-Live Canary Policy

Phase 11 is planning and gating only. It does not enable live trading,
exchange keys, or real orders.

A future canary may only be considered for crypto spot, with no leverage,
margin, futures, shorts, options, or withdrawals. Stage 1 future limits are
tiny by design: max order notional 25 USD, one open position, and explicit
daily/weekly loss caps. These limits are policy scaffolds, not active live
trading authority.

Before any future canary consideration, QuantOS must show dry-run proving
evidence, zero unresolved incidents, trade reconciliation evidence, dataset and
historical evidence, stoploss-on-exchange readiness, restricted API permission
scope, withdrawal-disabled proof, rollback drill evidence, and explicit human
approval. Even if those are satisfied, Phase 11 still returns LIVE_BLOCKED.

Phase 12 adds rehearsal proof. It can import a local permission manifest,
generate a rehearsal-only arming token, rehearse preflight, design stoploss
proof requirements, and summarize a final gate. It still returns LIVE_BLOCKED
and cannot place orders.

Phase 13 adds a default-off tiny-live execution lane scaffold. It remains
manual-only, tiny-notional, one-position-max, spot-only, and blocked unless
local credentials outside the repo plus permission, approval, arming, stoploss,
reconciliation, and final-gate checks all pass.
