# Planning Standard

## Required Sections

1. Objective
2. Non-goals
3. Repo evidence inspected
4. Affected surfaces
5. Proposed steps
6. Safety risks
7. Validation commands
8. Rollback or revert path
9. Role handoffs

## Scope Rules

- If live authority, keys, real orders, or broad autonomy appear, stop and require explicit user approval.
- If the task touches only instructions/docs, do not propose heavy smoke unless a referenced command or code path changed.
- If the task touches data/replay/calibration/validation, include the Sequence 1 targeted tests before full suite.
- If the task touches canary/live/security/configs, include live guards.
