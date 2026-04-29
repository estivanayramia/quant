# Readiness Policy

Readiness statuses are conservative:

- `NOT_STARTED`
- `INSUFFICIENT_EVIDENCE`
- `PROVING_IN_PROGRESS`
- `PROVING_UNSTABLE`
- `DRY_RUN_PROVEN`
- `LIVE_BLOCKED`

Phase 10 may accumulate enough safe evidence to call a dry-run process proven. It cannot mark the system live-ready, live-allowed, or tiny-live-allowed.
