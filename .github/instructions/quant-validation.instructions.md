---
applyTo: "src/quant_os/validation/**/*.py,tests/test_sequence1_validation_engine.py,reports/validation/**/*.json,reports/validation/**/*.md"
---

# Quant Validation Instructions

- Validation is behavioral system validation, not UI testing.
- Required scenarios include no edge, negative edge, stale data, corrupted data, reconciliation mismatch, kill switch, latency mismatch, partial fill, symbol/cap breach, and missing explanation.
- Missing reason codes or explanations are validation failures.
- Expected unsafe-action detection may intentionally produce a failing scenario outcome; distinguish "validator caught the unsafe behavior" from "system behaved safely."
- Reports must be machine-readable JSON and human-readable Markdown when the existing validation path expects both.
- Validation outputs must not imply live readiness.

Relevant checks:

- `python -m pytest tests/test_sequence1_validation_engine.py -q`
- `.\\make.cmd validation-smoke`
