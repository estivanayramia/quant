# Validation Steering

Start with the changed surface. Do not reflexively run deep smoke chains after every doc or instruction edit.

## Common Commands

| Surface | First checks |
| --- | --- |
| Instructions or skills only | internal consistency scan, file-reference validation, `git diff --check` |
| Python code style | `python -m ruff check .` |
| Live safety | `python -m quant_os.cli guard-live`; `python -m quant_os.cli freqtrade validate` |
| Data spine | `python -m pytest tests/test_sequence1_data_spine.py -q` |
| Crypto research | `python -m pytest tests/test_sequence1_crypto_research.py -q`; `.\\make.cmd crypto-research` |
| Replay | `python -m pytest tests/test_sequence1_replay.py -q`; `.\\make.cmd replay-smoke` |
| Calibration | `python -m pytest tests/test_sequence1_calibration.py -q`; `.\\make.cmd calibration-smoke` |
| Validation engine | `python -m pytest tests/test_sequence1_validation_engine.py -q`; `.\\make.cmd validation-smoke` |
| General integration | `.\\make.cmd smoke` |
| Full suite | `.\\make.cmd test` |

## Slow Command Rule

If a command produces no useful output for too long:

1. Inspect the make/CLI target.
2. Check stale locks and running Python processes.
3. Decompose to underlying commands.
4. Rerun only failed or affected checks after fixes.
