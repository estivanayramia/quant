# quant-os-factory

![CI](https://github.com/estivanayramia/quant/actions/workflows/ci.yml/badge.svg)

`quant-os-factory` is a local-first QuantOps foundation for deterministic research, event replay, simulated execution, risk review, and reporting.

It is not a generic AI trading bot, an LLM-controlled trader, or a get-rich-quick system. Milestone 1 is simulation only. It cannot place live trades, does not require broker or exchange keys, and does not include real broker integrations.

## Safety Warning

This repository is a deterministic simulation foundation. It does not guarantee profit, is not live-trading ready, and must not be used with real money in Milestone 1.

AI may research, critique, summarize, monitor, and propose improvements. Deterministic code owns execution, sizing, exits, reconciliation, risk decisions, kill switches, and state recovery.

## Install

```bash
make install
```

Python 3.11+ is required.

## Smoke Workflow

```bash
make smoke
```

The smoke workflow seeds deterministic demo data, validates data quality, runs baseline and placebo simulations, rebuilds DuckDB read models from the JSONL event ledger, generates reports, and runs a lightweight test subset.

## Common Commands

```bash
make seed-demo
make validate-data
make backtest
make tournament
make shadow
make rebuild
make report
make test
```

The Typer CLI is also available after install:

```bash
quant-os smoke
```

## Autonomous Safe Ops

Phase 2 adds an autonomous operations control plane for safe local/shadow/paper/dry-run-ready modes:

```bash
make autonomous
make watchdog
make drift
make alerts-test
```

Daemon mode is local-only and guarded:

```bash
quant-os autonomous daemon --interval-minutes 60
quant-os autonomous status
quant-os autonomous stop
```

This is now autonomous in safe local/shadow/paper/dry-run-ready modes, not live-money autonomous.

## Freqtrade Dry-Run Container

Phase 3 adds a disabled-by-default Freqtrade dry-run container lane:

```bash
make freqtrade-config
make freqtrade-export-strategy
make freqtrade-validate
make freqtrade-dry-run-check
make freqtrade-status
make phase3-smoke
```

This is now Freqtrade dry-run-container-ready, not live-trading-ready.

Phase 4 adds explicit dry-run operational commands:

```bash
make freqtrade-docker-check
make freqtrade-dry-run-status
make freqtrade-ingest-logs
make freqtrade-reconcile
make phase4-smoke
```

Container start remains explicit: `make freqtrade-dry-run-start`.

## Dry-Run Comparison Monitoring

Phase 5 adds local dry-run history, comparison metrics, divergence checks, artifact freshness checks, and strict promotion readiness:

```bash
make dryrun-history
make dryrun-compare
make dryrun-divergence-check
make dryrun-monitor-report
make dryrun-promote-check
make phase5-smoke
```

This remains dry-run evidence only. Live promotion reports `TINY_LIVE_BLOCKED`; the system is not live-trading-ready.

## Freqtrade Trade Artifact Reconciliation

Phase 6 adds local dry-run trade artifact scanning, ingestion, normalization, and trade-level reconciliation:

```bash
make freqtrade-artifacts-scan
make freqtrade-trades-ingest
make freqtrade-trades-normalize
make freqtrade-trade-reconcile
make freqtrade-trade-report
make phase6-smoke
```

If no structured Freqtrade dry-run trade artifacts exist, the system reports `UNAVAILABLE` or `WARN` rather than inventing trade evidence.

## Strategy Research Upgrade

Phase 7 adds deterministic feature building, market-structure feature interfaces, candidate strategies, ablation, walk-forward validation, regime testing, overfitting checks, and a conservative strategy leaderboard:

```bash
make features-build
make strategy-research
make strategy-ablation
make strategy-walk-forward
make strategy-regime-tests
make strategy-overfit-check
make strategy-leaderboard
make strategy-research-report
make phase7-smoke
```

ICT/SMC concepts are represented only as measurable research features, not assumed edge. No Phase 7 strategy can become live-ready; live promotion remains `TINY_LIVE_BLOCKED`.

## Dataset Evidence Hardening

Phase 8 adds deterministic offline expanded datasets, dataset manifests, quality reports, train/validation/test split metadata, leakage checks, evidence scoring, and research evidence reports:

```bash
make dataset-seed-expanded
make dataset-manifest
make dataset-quality
make dataset-splits
make dataset-leakage-check
make dataset-evidence-score
make research-evidence-report
make phase8-smoke
```

The expanded datasets are synthetic demo data, not real market data. Evidence scoring can improve research confidence but still blocks live promotion as `LIVE_BLOCKED`.

## Historical Data Ingestion

Phase 9 adds local/cache-first historical OHLCV import, normalization, manifests, quality checks, splits, leakage checks, and historical evidence reports:

```bash
make historical-provider-check
make historical-import-csv
make historical-normalize
make historical-manifest
make historical-quality
make historical-splits
make historical-evidence-score
make historical-research-report
make phase9-smoke
```

The default smoke path uses a tiny committed fixture. User-downloaded historical data is ignored under `data/historical/` and must include a source/license note. Historical data does not imply live readiness.

## Autonomous Proving Mode

Phase 10 adds multi-cycle proving evidence, incident history, streaks, freshness checks, stability checks, and proving readiness reports:

```bash
make proving-run-once
make proving-status
make proving-history
make proving-incidents
make proving-readiness
make proving-report
make phase10-smoke
```

Proving mode can accumulate dry-run evidence over time. It cannot unlock live trading; live promotion remains `LIVE_BLOCKED`.

## Repository Structure

- `src/quant_os/core`: framework-independent primitives, events, commands, errors, IDs, time.
- `src/quant_os/domain`: orders, fills, positions, strategy, risk, kill switch, quarantine, portfolio state.
- `src/quant_os/ports`: interfaces for market data, broker execution, AI, alerts, event store, read models, strategies, reports.
- `src/quant_os/adapters`: local Parquet data, simulated broker, mock AI, mock alerts, JSONL ledger, DuckDB projections, local reports.
- `src/quant_os/research`: deterministic strategies, backtests, metrics, placebo, ablation, walk-forward, tournaments, slippage stress.
- `src/quant_os/execution`: execution engine, OMS, PMS, state machine, fill simulator, reconciliation.
- `src/quant_os/risk`: risk firewall, limits, no-trade checks, sizing, drawdown.
- `src/quant_os/governance`: registry, promotion, quarantine, capital unlock rules.
- `src/quant_os/projections`: event-ledger rebuilds into DuckDB read models.
- `src/quant_os/ops`: health, logging, reporting, forensics.
- `configs`: local-safe defaults. Live trading is disabled by default.
- `docs`: architecture, risk, AI boundary, live-trading policy, future integrations, and ADRs.

## Architecture Overview

The system is a hexagonal modular monolith. The OMS/PMS and append-only event ledger are the authoritative write side. DuckDB is a disposable CQRS-lite read model used for analytics and reports. Commands mutate state only through deterministic domain and execution services. Every important state transition appends an immutable domain event.

The research control plane can generate candidate orders and reports. The execution control plane performs deterministic checks, simulated order handling, fills, reconciliation, and risk enforcement. The risk firewall has final authority.

## Milestone Roadmap

- Phase 1: local deterministic simulation foundation, event replay, risk firewall, mocked AI, mocked execution, reports.
- Phase 2: improved shadow mode, paper-mode abstraction, slippage/spread simulation, data drift checks, report history.
- Phase 3: Freqtrade dry-run adapter for crypto, still no live trading.
- Phase 4: Freqtrade dry-run operational runner, log ingestion, and reconciliation.
- Phase 5: Dry-run comparison monitoring, local history, divergence checks, and strict live-blocked promotion readiness.
- Phase 6: Freqtrade dry-run trade artifact ingestion and trade-level reconciliation, still with live promotion blocked.
- Phase 7: Strategy research upgrade, market-structure features, ablation, walk-forward validation, overfitting controls, and conservative leaderboard.
- Phase 8: Dataset expansion and evidence hardening with offline synthetic data, manifests, quality checks, leakage checks, and evidence scoring.
- Phase 9: Historical data ingestion and offline cache-first data lake controls.
- Phase 10: Autonomous proving mode and long-run evidence accumulation.
- Phase 11: Telegram/Discord alerts only, with no order authority.
- Phase 12: AI provider mesh for research/reporting only.
- Phase 13: Tiny live crypto canary only after extensive future gates.
- Phase 14: NautilusTrader evaluation if the simpler stack becomes a bottleneck.

## Live Trading Disclaimer

Milestone 1 disables live trading everywhere by default. No real broker SDKs, exchange SDKs, live endpoints, real API keys, leverage, options, futures, or withdrawal permissions are implemented.
