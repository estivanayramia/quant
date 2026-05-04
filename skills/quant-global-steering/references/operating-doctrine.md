# Quant Operating Doctrine

The repo is a local-first autonomous QuantOps factory.

## Authority Boundary

- AI may research, critique, summarize, monitor, explain, and help write code.
- Deterministic code owns data validation, features, replay/backtesting, OMS/PMS state, routing, sizing, exits, reconciliation, risk enforcement, kill switch, and live gating.
- AI may never place, resize, cancel, or authorize live risk-bearing orders.

## Current Strategic Priority

The repo is strongest in control plane, deterministic execution boundaries, governance, reporting, fake/default-off live posture, canary gates, and conservative research plumbing.

The repo is weakest in edge discovery, venue data, replay realism, manipulation and stale-data modeling, calibration from real venue behavior, and scenario validation.

Prefer edge + data + replay + calibration + validation before broader live work.

## Safety Invariants

- Live remains default-off.
- CI and fresh checkouts remain fake-only and blocked-real.
- No real keys in the repo.
- No real orders in tests.
- Kill switch wins.
- External/local divergence pauses activity.
- Stale, corrupt, missing, or future-leaking data blocks or warns explicitly.
- Calibration must be able to say "no edge, do nothing."
