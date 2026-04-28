# Historical Data Ingestion

Phase 9 adds a local, cache-first historical OHLCV ingestion lane.

This does not enable live trading, broker connectivity, exchange trading keys, paid data, or internet access in CI. Imports are explicit-command only and write normalized data under ignored `data/historical/`.

## Import

Expected canonical columns are `timestamp`, `symbol`, `open`, `high`, `low`, `close`, and `volume`. Common aliases such as `date`, `ticker`, `o`, `h`, `l`, `c`, and `vol` are mapped into the canonical schema.

```powershell
make.cmd historical-import-csv
make.cmd historical-normalize
make.cmd historical-manifest
make.cmd historical-quality
make.cmd historical-splits
make.cmd historical-evidence-score
make.cmd historical-research-report
```

The default command uses a tiny committed fixture for offline smoke checks. User-downloaded datasets must remain local and ignored by git.

## Provider Policy

`LOCAL_FILE` is available by default. Network-backed public provider scaffolds are disabled by default and do not run in tests or CI.

## Caveats

Historical data improves research evidence, but it does not imply profitability, live readiness, or real-money safety.
