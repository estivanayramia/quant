# Dry-Run Comparison Monitoring

Phase 5 adds an evidence layer over the safe Freqtrade dry-run lane. It stores local history, compares generated Freqtrade artifacts with QuantOS expectations, checks divergence, and writes monitoring reports.

This is not live trading. It does not use exchange API keys, does not require Docker in CI, and does not start Freqtrade autonomously.

## Commands

- `make.cmd dryrun-history`
- `make.cmd dryrun-compare`
- `make.cmd dryrun-divergence-check`
- `make.cmd dryrun-monitor-report`
- `make.cmd dryrun-promote-check`
- `make.cmd dryrun-status`
- `make.cmd phase5-smoke`

## What Is Compared

- `dry_run` must remain `true`.
- Live trading flags must remain disabled.
- Generated pair universe, timeframe, strategy name, stake amount, and max open trades are compared against QuantOS config.
- Strategy and config hashes are tracked over time.
- Freqtrade log warnings, errors, dry-run markers, and live-mode danger strings are monitored.
- QuantOS risk caps are compared against generated Freqtrade dry-run config.

Trade-level comparison is intentionally reported as unavailable until structured Freqtrade dry-run trade artifacts are ingested. The system does not fake that reconciliation.

## Promotion Readiness

Phase 5 can report `DRY_RUN_READY` for local dry-run monitoring evidence when safety checks pass, but live promotion always remains `TINY_LIVE_BLOCKED`.

Live remains blocked because there is no multi-week dry-run evidence, no real exchange reconciliation, no stoploss-on-exchange proof, no API-key permission verification, no live canary policy implementation, and no human approval gate.

## Reports

Reports are written under `reports/dryrun/`:

- `latest_history.json`
- `latest_comparison.json`
- `latest_divergence.json`
- `latest_promotion_readiness.json`
- `latest_monitoring_report.json`
- `latest_monitoring_report.md`

Generated reports are local artifacts and are not source of truth for OMS/PMS state.
