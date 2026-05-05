# Validation Rules

## Commands

- List scenarios: `python -m quant_os.cli validation list-scenarios`
- Single scenario: `python -m quant_os.cli validation run --scenario <id>`
- All scenarios: `.\\make.cmd validation-smoke`
- Targeted test: `python -m pytest tests/test_sequence1_validation_engine.py -q`
- Full Sequence 1: `.\\make.cmd sequence1-smoke`

## Report Checks

- JSON and Markdown should both exist for expected scenario reports.
- Summary must include unsafe-action failure count and blocked-correctly count.
- Outputs must include `live_trading_enabled: False` where the repo convention expects it.
