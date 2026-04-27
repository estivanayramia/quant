# Freqtrade Dry-Run Container

Phase 3 adds a Freqtrade dry-run container lane for crypto simulation comparison.

## What This Does

- Generates a dry-run-only Freqtrade config.
- Exports a minimal deterministic strategy scaffold.
- Validates that live trading, keys, leverage, futures, margin, shorts, Telegram, and API server controls stay disabled.
- Provides a Docker Compose profile for manual dry-run inspection.
- Adds status, manifest, and autonomy-report integration.

## What This Does Not Do

- It does not place live trades.
- It does not use exchange API keys.
- It does not pull Freqtrade images during tests.
- It does not run Freqtrade automatically.
- It does not implement tiny live canary.

## Commands

```bash
make freqtrade-config
make freqtrade-export-strategy
make freqtrade-validate
make freqtrade-dry-run-check
make freqtrade-status
make freqtrade-command-preview
make phase3-smoke
```

## Manual Docker Preview

After generating and validating config:

```bash
docker compose --profile freqtrade-dry-run run --rm freqtrade-dry-run --help
```

The Docker profile is not started by default. Tests do not require Docker Desktop, internet, or a Freqtrade image pull.

## Safety Rules

Generated config must keep `dry_run: true`, `live_trading_allowed: false`, `trading_mode: spot`, blank exchange credentials, Telegram disabled, API server disabled, no leverage, no futures, no margin, and no shorting.

If exchange key environment variables are present, config generation refuses to run. Do not add withdrawal permissions. Do not commit `.env`.

## Future Gates

Tiny live crypto canary remains a future phase and requires weeks of dry-run/paper stability, reconciliation tests, slippage tests, kill-switch drills, API permission review, no withdrawal permission, and explicit human approval.

## Windows / Docker Desktop

If Docker is unavailable, status will report `docker_available: false`. You can still generate config, validate safety, export strategy, and run tests.

