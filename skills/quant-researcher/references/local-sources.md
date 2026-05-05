# Local Sources

Use these before external material:

- Doctrine: `STRATEGY_CONSTITUTION.md`, `README.md`, `docs/ai_boundary.md`, `docs/risk_policy.md`, `docs/live_trading_policy.md`
- Architecture: `docs/architecture.md`, `docs/adr/*`
- Commands: `make.cmd`, `src/quant_os/cli.py`, `.github/workflows/ci.yml`
- Sequence 1: `src/quant_os/data`, `src/quant_os/research/crypto`, `src/quant_os/research/calibration`, `src/quant_os/replay`, `src/quant_os/validation`
- Tests: `tests/test_sequence1_*.py`, safety tests under `tests/test_live*.py`, `tests/test_canary*.py`, `tests/test_freqtrade_safety_guard.py`
- Configs: `configs/*.yaml`

Use `Select-String` or `rg` if available; prefer targeted searches over broad file reads.
