---
applyTo: "src/quant_os/core/**/*.py,src/quant_os/domain/**/*.py,src/quant_os/execution/**/*.py,src/quant_os/risk/**/*.py,src/quant_os/governance/**/*.py,src/quant_os/ports/**/*.py"
---

# Quant Core Instructions

- Treat OMS, PMS, risk, domain events, and kill-switch behavior as authoritative deterministic state.
- Preserve fail-closed behavior for order decisions, state transitions, risk checks, and reconciliation.
- Candidate strategy output is input only. It must not override risk, kill switch, quarantine, or position limits.
- Every new rejection/block path needs a stable reason code.
- Avoid silent state mutation. Important state transitions should remain event-backed where the surrounding module already uses events.
- Validate with the smallest affected tests first, then broader smoke only when the core path changed.

Relevant checks:

- `python -m pytest tests/test_risk_firewall.py tests/test_event_replay.py -q`
- `python -m pytest tests/test_order_state_machine.py tests/test_position_tracker.py -q`
- `.\\make.cmd smoke`
