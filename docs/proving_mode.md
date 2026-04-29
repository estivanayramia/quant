# Autonomous Proving Mode

Phase 10 records autonomous safe-mode runs over time and turns them into proving evidence.

This is dry-run/simulation proving only. It does not enable live trading, broker keys, exchange keys, `dry_run: false`, leverage, futures, margin, shorts, options, Telegram command authority, or AI execution authority.

## Commands

```powershell
make.cmd proving-run-once
make.cmd proving-status
make.cmd proving-history
make.cmd proving-incidents
make.cmd proving-readiness
make.cmd proving-report
```

## What Is Tracked

- autonomous run status;
- success and failure streaks;
- incidents and unresolved incident counts;
- safety/data/leakage/reconciliation blockers;
- dry-run monitoring evidence;
- dataset and historical evidence;
- strategy leaderboard stability;
- report freshness.

`DRY_RUN_PROVEN` can be reported after repeated safe cycles in future proving windows, but live promotion remains `LIVE_BLOCKED`.
