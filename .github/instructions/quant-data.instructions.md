---
applyTo: "src/quant_os/data/**/*.py,src/quant_os/data/providers/**/*.py,configs/data.yaml,configs/datasets.yaml,configs/historical_data.yaml,tests/test_*data*.py,tests/test_*dataset*.py,tests/test_historical*.py,tests/test_sequence1_data_spine.py"
---

# Quant Data Instructions

- Data quality is a trading safety boundary, not a convenience check.
- Normalize timestamps to UTC and symbols to canonical venue/research form before joins, features, replay, or labels.
- Stale, missing, duplicate, non-monotonic, corrupt, future-leaking, or schema-incomplete data must block or clearly warn. Never fill through bad data silently.
- Preserve raw/normalized/derived separation and manifest/freshness metadata.
- Public network providers must be optional and disabled in CI paths. Tests must use fixtures or generated offline data.
- Do not add real keys, paid data assumptions, or internet-required core tests.

Relevant checks:

- `python -m pytest tests/test_sequence1_data_spine.py -q`
- `python -m pytest tests/test_dataset_quality.py tests/test_historical_quality.py -q`
- `python -m quant_os.cli data validate`
