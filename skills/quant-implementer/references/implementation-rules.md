# Implementation Rules

## Must Preserve

- AI support-only boundary.
- Deterministic risk and execution authority.
- Live default-off, fake-only CI, blocked-real fresh checkouts.
- Kill switch priority.
- External/local divergence blocking.
- No real keys, no real orders in tests.

## Editing Rules

- Use existing module style and tests.
- Prefer structured parsers and typed models where the repo already uses them.
- Do not add broad abstractions for one narrow change.
- Do not change trading behavior while editing docs, instructions, or skills.
- Do not stage, commit, push, or open a PR unless explicitly asked.

## Generated Artifacts

Reports and data under ignored runtime folders should not be committed unless the task explicitly asks for fixture updates.
