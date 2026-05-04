# Scenario Map

Required Sequence 1 scenarios:

- `no_edge_no_trade`
- `negative_edge_no_trade`
- `stale_data_block`
- `corrupted_data_block`
- `reconciliation_mismatch_block`
- `kill_switch_hard_stop`
- `latency_mismatch_degrade_or_block`
- `partial_fill_state_handling`
- `symbol_cap_breach_hard_fail`
- `missing_explanation_validation_fail`

The missing-explanation scenario is supposed to surface an unsafe-action failure. Treat it as proof that the validator catches unsafe behavior, not as permission to weaken the scenario.
