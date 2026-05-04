# Debugging Standard

## Common Failure Classes

- Replay: cost assumptions, latency alignment, partial fill state, event ordering, equity curve mismatch.
- Strategy: leaked labels, stale features, placebo beating candidate, low trade count, regime instability.
- Data: schema drift, timezone mismatch, duplicate timestamp, stale artifact, bad symbol normalization.
- Dry-run/live: config flag drift, missing external local settings, blocked-real adapter, fake/real mismatch.
- Validation: expected unsafe failure misread as infrastructure failure, missing report, missing reason code.

## Evidence To Capture

- Exact command and exit code.
- First failing assertion or reason code.
- Relevant config values.
- Input row/event/fill that first diverges.
- Whether generated artifacts are stale.

## Hand Off

Give the implementer a minimal failing command and a root-cause hypothesis. Do not patch from the debugger role.
