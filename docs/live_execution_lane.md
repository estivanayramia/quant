# Tiny-Live Crypto Canary Execution Lane

Phase 13 adds a narrow, default-off tiny-live crypto canary lane.

This is not broad live trading. The base install cannot place a real order
because live execution is disabled, the real exchange transport is unavailable
by default, credentials must live outside the repo, and every gate must pass
before any fire attempt is considered.

## Scope

- Crypto spot only.
- Allowlist: `BTC/USDT`, `ETH/USDT`.
- Max order notional: 25 USD.
- Max open positions: 1.
- One explicit fire attempt at a time.
- No autonomous live start.

## Required Gates

- Live trading guard.
- Live execution guard.
- Local credential file outside the repository.
- Permission manifest with no forbidden scopes.
- Human approval registry record.
- Arming token.
- Final canary gate.
- Stoploss-on-exchange capability proof.
- Symbol allowlist and notional cap.
- Max open-position check.
- Kill switch check.
- Incident and proving-readiness checks.
- Reconciliation before and after an attempt.

## Commands

- `make.cmd canary-exchange-capabilities`
- `make.cmd canary-live-prepare`
- `make.cmd canary-live-preflight`
- `make.cmd canary-live-status`
- `make.cmd canary-live-reconcile`
- `make.cmd canary-live-stop`
- `make.cmd canary-live-report`

`make.cmd canary-live-fire` exists, but it remains blocked by default and
requires `--confirm-live-fire`, symbol, notional, and all gates.

## CI Behavior

CI never uses real credentials, never connects to an exchange, never calls
Docker, and never runs a real live fire attempt. Unit tests use the fake adapter
only.

## Phase 14 Single-Exchange Adapter

Phase 14 adds exactly one real-adapter path behind the same canary port:
`kraken_spot_ccxt`. It is still disabled by default. A fresh checkout reports
fake-only capability, no real transport, and no real order possibility.

The real adapter is unavailable unless a local settings file outside the repo
explicitly selects spot-only mode, real adapter enablement, live transport
enablement, and documented stoploss-on-exchange support. Optional dependency
or settings problems block the adapter instead of silently falling back to a
real order path.

`canary-live-fire` keeps every Phase 13 gate: explicit confirmation, symbol
allowlist, notional cap, one open position, permission manifest, approval,
arming token, final gate, stoploss proof, reconciliation, and kill switch.
