# Codex Goals Guardrails

The experimental `/goal` feature is enabled locally for Codex, but it is not a default way to run this repo.

Use `/goal` only when success is objectively defined, supervised, and bounded by concrete stop conditions. Good examples are narrow verification loops, a specified failing test that must pass, or a small cleanup with a crisp expected Git status.

Avoid `/goal` for vague prompts such as "make this better", open-ended profit seeking, broad architecture exploration, live trading, wallet/signing/order flows, or anything without a pass/fail condition. It can be token-hungry because it continues planning, checking, and iterating until a goal is satisfied or stopped, so ambiguous goals can burn context and compute without improving profitability evidence.

For QuantOS, `/goal` must stay support-only. It must not place, resize, cancel, or authorize live orders; bypass risk or kill switches; grant AI execution authority; broaden prediction-market execution; or promote weak research toward live. Deterministic code remains responsible for validation, replay, OMS/PMS state, routing, sizing, exits, reconciliation, risk enforcement, kill switches, and live gating.
