# Agent Guide For Quant

This repository is a local-first autonomous QuantOps factory. Agents must optimize for truthful research, deterministic safety, and validation before live expansion.

## Audit

- No previous `.github/copilot-instructions.md`, `.github/instructions/`, `AGENTS.md`, `CLAUDE.md`, or repo-local `skills/` existed.
- Doctrine already lived in `README.md`, `STRATEGY_CONSTITUTION.md`, and `docs/*`, but it was not routed into Copilot path rules or Codex roles.
- The main ambiguity risk was role overlap: review, debugging, validation, security, and implementation could all touch similar surfaces without clear read-only/editing boundaries.
- The biggest improvement is a two-layer system: Copilot gets universal and path-specific rules; Codex gets role skills with lean `SKILL.md` files and deeper references.

## Instruction Architecture

- `.github/copilot-instructions.md`: universal repo doctrine, safety red lines, validation steering, and precedence.
- `.github/instructions/*.instructions.md`: path-specific rules for core, data, replay, validation, live safety, and research.
- `skills/*`: Codex-native role skills. These are role-specific and should not duplicate every repo rule inline.
- `skills/*/references/*`: deeper doctrine, validation maps, and role checklists loaded only when useful.

No `CLAUDE.md` is added. The repo does not need a second agent-facing doctrine file because `AGENTS.md`, Copilot instructions, and the Codex skills cover the split without duplication.

## Role Matrix

| Role | Editing | Responsibility | Main Handoffs |
| --- | --- | --- | --- |
| `quant-global-steering` | Compatible with either | Persistence, verification, todo tracking, no fake tool claims, no auto-commit | Any role |
| `quant-planner` | Read-only | Smallest credible plan, affected systems, validation, rollback, safety risks | Implementer, security reviewer |
| `quant-researcher` | Read-only | Repo evidence, files, configs, tests, prior docs, freshness-sensitive external checks | Planner, implementer |
| `quant-implementer` | Editing | Safe scoped edits, validation mapping, no live broadening | Reviewer, debugger, validation tester, security reviewer |
| `quant-reviewer` | Read-only | Findings-first review of correctness and safety regressions | Implementer, security reviewer |
| `quant-debugger` | Read-only | Reproduce-first diagnosis, root cause, no fixes | Implementer, validation tester |
| `quant-validation-tester` | Read-only by default | Scenario, replay, calibration, and report validation | Implementer, QA gate |
| `quant-security-risk-reviewer` | Read-only | Secrets, live enablement, adapter authority, blast radius | Implementer, reviewer |
| `quant-qa-gate` | Read-only | Final confidence gate, coverage gaps, false-output risk | Planner, implementer |

## Migration Notes

- Removed website-specific roles and browser/visual QA concepts.
- Merged replay auditing into `quant-reviewer` and `quant-validation-tester` instead of creating a separate default role.
- Merged canary ops review into `quant-security-risk-reviewer` and live-safety path instructions.
- Moved repeated doctrine into `quant-global-steering/references/operating-doctrine.md`.
- Moved command selection into `quant-implementer/references/validation-map.md` and Copilot path files.
- Created the missing `quant-implementer` as the only default editing role.

## Repository References

- Doctrine: `STRATEGY_CONSTITUTION.md`, `docs/ai_boundary.md`, `docs/live_trading_policy.md`, `docs/risk_policy.md`
- Sequence 1: `src/quant_os/data`, `src/quant_os/research/crypto`, `src/quant_os/research/calibration`, `src/quant_os/replay`, `src/quant_os/validation`
- Safety gates: `src/quant_os/security`, `src/quant_os/live_canary`, `src/quant_os/canary`
- Validation commands: `make.cmd`, `src/quant_os/cli.py`, `.github/workflows/ci.yml`

## Default Agent Rules

- Read before editing.
- Keep live default-off.
- Prefer targeted checks, then broader checks only when justified.
- Do not commit, push, or open a PR unless the user explicitly asks.
- Make uncertainty and failed checks visible.
