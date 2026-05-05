---
name: quant-global-steering
description: Use when working in the quant repo and the task needs persistence, verification discipline, todo tracking, safe scope control, or protection against unfinished agent work.
---

# Quant Global Steering

Use this as the clean repo steering layer. It applies to planning, read-only work, implementation, review, debugging, validation, and final QA.

## Core Rules

- Keep going until the requested work is genuinely handled or blocked with evidence.
- Track non-trivial work with todos and update status as work changes.
- Inspect repo context before changing files.
- Prefer root-cause fixes over symptom patches.
- Never pretend a command, test, search, or tool call happened.
- Do not commit, push, or open a PR unless the user explicitly asks.
- Keep live default-off and fail closed.
- Use targeted checks first; run heavier checks only when the changed surface justifies them.

## Role Compatibility

Read-only roles may inspect, diagnose, review, and recommend, but must not edit files. Editing belongs to `quant-implementer` or an explicitly authorized implementation flow.

## References

- Read `references/operating-doctrine.md` when changing safety, risk, research, live/canary, or validation behavior.
- Read `references/validation-steering.md` before choosing commands.
- Read `references/implementation-standard.md` before editing or handing work to an implementer.

## Stop Conditions

Stop and report clearly when:

- A requested change would broaden live authority.
- Required evidence contradicts the requested conclusion.
- The repo is dirty with unrelated changes that would be staged or overwritten.
- A validation command fails and the root cause is not yet understood.
