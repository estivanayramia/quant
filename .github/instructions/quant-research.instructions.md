---
applyTo: "src/quant_os/research/**/*.py,src/quant_os/features/**/*.py,configs/strategy_research.yaml,configs/strategies.yaml,tests/test_strategy*.py,tests/test_*research*.py,tests/test_sequence1_crypto_research.py,tests/test_sequence1_calibration.py"
---

# Quant Research Instructions

- Research code may discover candidates; it must not claim live readiness or self-promote strategies.
- Prefer one narrow honest battlefield over many weak edges.
- Compare candidates against no-trade and placebo/random baselines.
- Watch for leakage, overfit, low trade count, weak placebo margin, regime sensitivity, stale data, and missing cost assumptions.
- Calibration must be able to say "no edge, do nothing."
- Reports should make limitations and failure modes explicit.

Relevant checks:

- `python -m pytest tests/test_sequence1_crypto_research.py tests/test_sequence1_calibration.py -q`
- `.\\make.cmd crypto-research`
- `.\\make.cmd calibration-smoke`
