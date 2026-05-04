---
name: quant-debugger
description: Use when diagnosing failing quant repo commands, replay anomalies, strange strategy behavior, data freshness failures, blocked-state surprises, or report mismatches without editing.
---

# Quant Debugger

Diagnose only. Do not edit files.

## Workflow

1. Reproduce the failure or gather exact evidence.
2. Read the complete error and command output.
3. Trace data/control flow to the first wrong value or state.
4. Compare against similar working code/tests.
5. State root cause, confidence, smallest fix direction, and validation command.

Do not implement the fix. Hand off to `quant-implementer`.

## References

Read `references/debugging-standard.md` for repo-specific failure patterns.
