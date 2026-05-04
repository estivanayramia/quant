# QA Scope

## Minimum Final Checks

- `git status --short --branch`
- `git diff --check`
- Relevant targeted tests or consistency checks.
- Safety commands if any live/canary/config/security surface changed.

## False-Output Risks

- A report says "ready" when live is still blocked.
- A validation scenario catches unsafe behavior but is summarized as ordinary failure without context.
- A profitable replay omits costs, slippage, latency, or capacity.
- A strategy report omits placebo/no-trade baseline.
- A docs/instruction change points to files or commands that do not exist.

## Handoff

State what changed, what was checked, what was intentionally unchanged, and the exact next command for the user.
