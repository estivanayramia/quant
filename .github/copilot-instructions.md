# Quant Repo Instructions

This repo is a local-first autonomous QuantOps factory. Treat it as production-risk software even when code paths are dry-run or simulated.

## Doctrine

- AI may research, critique, summarize, monitor, explain, and help implement code.
- Deterministic code owns data validation, feature generation, replay/backtesting, OMS/PMS state, routing, sizing, exits, reconciliation, risk, kill switch, and live gating.
- AI must never place live orders, resize live orders, cancel risk-bearing orders, bypass risk, bypass the kill switch, or grant itself execution authority.
- Live trading remains default-off. Real keys, broad unattended live expansion, and AI execution authority are out of scope unless an explicit later human-approved phase says otherwise.
- Current priority is edge + data + replay + calibration + validation before broader live work.

## Instruction Precedence

Use the most specific instruction that applies:

1. `.github/instructions/**/*.instructions.md` for path-specific rules.
2. This repository-wide file for universal rules.
3. `AGENTS.md` and `skills/*` for role behavior and deeper references.

If two instructions conflict, choose the safer option: no live authority, fail closed, run narrower validation, and ask before changing scope.

## Work Standard

- Inspect local files, configs, tests, and reports before editing.
- Keep changes small, mergeable, and mapped to validation commands.
- Preserve existing architecture and safety boundaries.
- Do not rebuild completed phases unless the task explicitly requires it.
- Do not stage, commit, push, or open PRs unless explicitly asked.
- Never claim a command ran unless it actually ran in this workspace.

## Validation Steering

Prefer targeted checks for the changed surface before full-suite work.

Common checks:

- Baseline safety: `python -m quant_os.cli guard-live`
- Freqtrade dry-run guard: `python -m quant_os.cli freqtrade validate`
- General smoke: `.\\make.cmd smoke`
- Full tests: `.\\make.cmd test`
- Sequence 1: `.\\make.cmd sequence1-smoke`
- Data spine: `python -m pytest tests/test_sequence1_data_spine.py -q`
- Crypto research: `python -m pytest tests/test_sequence1_crypto_research.py -q`
- Replay: `python -m pytest tests/test_sequence1_replay.py -q`
- Calibration: `python -m pytest tests/test_sequence1_calibration.py -q`
- Validation engine: `python -m pytest tests/test_sequence1_validation_engine.py -q`

If a command appears stale, recursive, or too heavy, inspect the target and decompose it instead of waiting blindly.

## Safety Red Lines

- No real secrets in repo files, tests, fixtures, reports, or docs.
- No `dry_run: false`, live flags, leverage, margin, futures, shorts, options, withdrawal permissions, or exchange keys in committed defaults.
- No direct imports of real broker/exchange SDKs except the explicitly guarded adapter exception already tested by `tests/test_smoke.py`.
- External/local divergence, stale data, corrupt data, reconciliation mismatch, kill switch activation, or missing reason codes must block or fail closed.
