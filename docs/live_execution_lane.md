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
