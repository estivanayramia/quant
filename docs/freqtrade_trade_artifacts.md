# Freqtrade Trade Artifact Reconciliation

Phase 6 adds conservative ingestion for Freqtrade dry-run trade artifacts. It scans local artifact folders, parses safe JSON/JSONL/log/SQLite sources when present, normalizes trade-like rows into QuantOS canonical dry-run records, and compares them with QuantOS expected trade/fill data where possible.

This is still dry-run only. It does not start Freqtrade, does not contact an exchange, does not use keys, and does not unlock live trading.

## Commands

- `make.cmd freqtrade-artifacts-scan`
- `make.cmd freqtrade-trades-ingest`
- `make.cmd freqtrade-trades-normalize`
- `make.cmd freqtrade-trade-reconcile`
- `make.cmd freqtrade-trade-report`
- `make.cmd phase6-smoke`

Dry-run aliases:

- `make.cmd dryrun-trade-reconcile`
- `make.cmd dryrun-trade-report`

## Artifact Handling

The scanner searches `freqtrade/user_data` and `reports/freqtrade` by default. It excludes suspicious secret/key/credential filenames and refuses to treat missing trade data as proof of readiness.

Supported artifact classes:

- JSON trade exports
- JSONL trade events
- local logs with obvious dry-run trade-like lines
- read-only SQLite files when available

Unknown schemas are preserved as raw payloads. If no structured trade artifacts exist, reconciliation reports `UNAVAILABLE` or `WARN` honestly.

## Fail-Closed Conditions

Trade reconciliation fails on live-mode evidence, credentials, `dry_run: false`, live flags, futures, margin, leverage above one, shorting, missing safety config, or core Freqtrade guard failure.

Live promotion remains `TINY_LIVE_BLOCKED`.
