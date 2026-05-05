# Implementation Standard

## Before Editing

- Read relevant modules, tests, configs, and docs.
- Identify the smallest credible change.
- Map the changed surface to validation commands.
- Check `git status --short --branch`.

## While Editing

- Preserve user changes.
- Do not reset, checkout, or delete unrelated work.
- Keep generated artifacts out of commits unless explicitly intended.
- Maintain live default-off and fake-only CI behavior.
- Add or update tests when behavior changes.

## Before Finishing

- Run fresh validation for the changed surface.
- State exact commands and results.
- Report known limitations and intentionally disabled paths.
- Do not claim success from assumptions or old output.
