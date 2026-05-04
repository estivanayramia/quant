---
name: quant-qa-gate
description: Use when ending quant repo work and verifying coverage, validation fit, false-output risk, diagnosability gaps, and readiness to hand off.
---

# Quant QA Gate

Final QA only. Do not edit files unless explicitly reassigned.

## Gate Questions

- Did the checks match the changed surface?
- Are any outputs user-believable but false or overconfident?
- Are replay, calibration, validation, and reports still diagnosable?
- Are live, canary, and security controls still default-off and gated?
- Are known limitations explicit?
- Is there any uncommitted generated artifact that should be ignored or removed?

## Output

Return pass/fail with evidence, residual risks, and exact next command.

## References

Read `references/qa-scope.md` for the final checklist.
