# Datasets

Phase 8 adds a deterministic offline dataset layer for research evidence hardening.

The expanded demo dataset is synthetic, reproducible, and local-only. It is not real market data and must not be treated as proof of live trading readiness.

## Commands

```bash
make dataset-seed-expanded
make dataset-manifest
make dataset-quality
make dataset-splits
make dataset-leakage-check
make dataset-evidence-score
make research-evidence-report
```

Generated Parquet data is written under `data/demo_expanded/` and is ignored by git. Reports are written under `reports/datasets/` and `reports/evidence/`.

## Coverage

The default generator creates multiple symbols, multiple timeframes, trend/chop/volatility regimes, volume spikes, and gap-like synthetic events. Crypto symbols include weekend timestamps. Equity symbols use rough session-like intraday timestamps.

## Manifest

The manifest records dataset ID, generator version, schema version, random seed, symbols, timeframes, row counts, paths, timestamps, and file hashes.

## Caveat

Synthetic data can test plumbing, validation, leakage checks, and reproducibility. It cannot prove a strategy has market edge.
