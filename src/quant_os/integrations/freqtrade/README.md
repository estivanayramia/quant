# Freqtrade Dry-Run Scaffold

Phase 3 provides a Docker-profile Freqtrade dry-run lane. It does not install, start, or connect Freqtrade during tests. Generated configs keep `dry_run: true`, blank keys, spot-only trading, disabled Telegram/API server, and `live_trading_allowed: false`.

Manual preview:

```bash
docker compose --profile freqtrade-dry-run run --rm freqtrade-dry-run --help
```

Do not add exchange keys to generated configs.

