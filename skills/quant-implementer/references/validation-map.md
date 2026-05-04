# Validation Map

Use the smallest relevant checks first.

| Change surface | Commands |
| --- | --- |
| Instructions, skills, docs only | `git diff --check`; internal reference/path scan |
| Python style | `python -m ruff check .` |
| Data spine | `python -m pytest tests/test_sequence1_data_spine.py -q` |
| Crypto research | `python -m pytest tests/test_sequence1_crypto_research.py -q`; `.\\make.cmd crypto-research` |
| Replay | `python -m pytest tests/test_sequence1_replay.py -q`; `.\\make.cmd replay-smoke` |
| Calibration | `python -m pytest tests/test_sequence1_calibration.py -q`; `.\\make.cmd calibration-smoke` |
| Validation engine | `python -m pytest tests/test_sequence1_validation_engine.py -q`; `.\\make.cmd validation-smoke` |
| Live/canary/security/config | `python -m quant_os.cli guard-live`; `python -m quant_os.cli freqtrade validate`; targeted live/canary tests |
| Broad integration | `.\\make.cmd smoke` |
| Pre-PR/full confidence | `.\\make.cmd test` |

Sequence 1 smoke intentionally includes a validation summary that catches a missing-explanation failure. Do not "fix" that by weakening the scenario.
