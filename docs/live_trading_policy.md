# Live Trading Policy

Live trading is disabled in Milestone 1.

Phase 3 adds a Freqtrade dry-run container scaffold only. It must keep `dry_run: true`, blank exchange credentials, no withdrawals, spot-only trading, no leverage, no futures, no margin, no shorts, disabled Telegram command authority, and disabled API server by default.

Phase 4 may start and stop a Docker dry-run container only through explicit user commands. The autonomous daemon must not start Freqtrade by default.

Phase 5 adds dry-run comparison monitoring only. It cannot enable live trading, cannot set `dry_run` to false, cannot use exchange keys, and cannot promote a strategy to live.

Phase 6 adds trade artifact ingestion and trade-level reconciliation only. It reads local dry-run artifacts conservatively, never contacts an exchange, and still keeps live promotion blocked.

Phase 7 adds strategy research upgrades only. Candidate strategies, market-structure features, ablation, walk-forward validation, overfitting checks, and leaderboards cannot unlock live trading.

Phase 8 adds offline synthetic datasets, manifests, quality checks, leakage checks, and evidence scoring. These reports cannot unlock live trading.

Phase 9 adds local/cache-first historical data imports only. Historical data reports cannot authorize broker keys, exchange keys, leverage, margin, futures, shorts, options, `dry_run: false`, or live trading.

Phase 10 adds autonomous proving mode and long-run evidence accumulation. Proving readiness can describe dry-run evidence only and still reports live promotion as `LIVE_BLOCKED`.

Phase 11 adds tiny-live canary policy gates only. It does not add a live adapter, exchange keys, or a `dry_run: false` path. Canary reports are planning artifacts and always keep live promotion blocked.

Phase 12 adds canary rehearsal proof only: local permission manifest import, arming token rehearsal, preflight rehearsal, stoploss-on-exchange proof design, and final gate reporting. It still does not add exchange connectivity or live execution.

Future tiny-live gates require weeks of shadow and paper stability, reconciliation tests, slippage tests, kill-switch tests, explicit API-key rules, no withdrawal permissions, recommended IP allowlists, tiny max order notional, and max open positions of 1.

Tiny live crypto may only be considered after the gates and through a later Freqtrade path. Equities live trading may only be considered after broker restrictions, order rules, and session behavior are verified.

This repo is not safe for real money.
