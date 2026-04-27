# Architecture

`quant-os-factory` is a hexagonal modular monolith. The domain core is framework-independent and owns orders, fills, positions, risk decisions, kill-switch state, strategy quarantine state, capital unlock stages, no-trade decisions, and domain events.

The research control plane produces candidate orders, backtests, comparisons, reports, and AI-assisted summaries. The execution control plane owns deterministic risk review, OMS/PMS mutation, simulated execution, reconciliation, and event logging.

The OMS/PMS and append-only JSONL event ledger are the authoritative write side. DuckDB is a disposable CQRS-lite read/query layer. If DuckDB is deleted, it can be rebuilt from the ledger.

AI output is support-only. It can critique strategies and summarize runs, but it cannot place orders, size positions, override risk, change limits, or deactivate the kill switch.

Future integrations are adapters behind ports. Milestone 1 implements only local Parquet data, simulated broker, mock AI, mock alerts, JSONL events, DuckDB read models, and local reports.

