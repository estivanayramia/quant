# Risk Review Map

## High-Risk Paths

- `src/quant_os/security`
- `src/quant_os/live_canary`
- `src/quant_os/canary`
- `configs/live*.yaml`
- `configs/canary*.yaml`
- `configs/freqtrade.yaml`
- `configs/integrations.yaml`
- `.env*`, credentials, local settings, generated reports containing keys

## Required Questions

- Can this change enable live trading by default?
- Can CI or a fresh checkout contact a real exchange?
- Can AI/autonomy start live fire or bypass a gate?
- Can keys enter the repo, logs, reports, fixtures, or PR body?
- Can reconciliation mismatch be ignored?
- Does kill switch still override every subsystem?

## Common Checks

- `python -m quant_os.cli guard-live`
- `python -m quant_os.cli freqtrade validate`
- `python -m pytest tests/test_smoke.py::test_no_real_broker_sdks_imported -q`
- Targeted live/canary/security tests for touched modules.
