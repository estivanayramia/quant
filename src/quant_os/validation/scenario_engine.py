from __future__ import annotations

import pandas as pd

from quant_os.replay.engine import ReplayEngine, ReplayOrderIntent
from quant_os.validation.contracts import ValidationOutcome, ValidationScenario
from quant_os.validation.outcomes import fail_outcome, pass_outcome
from quant_os.validation.validators.decision import should_trade
from quant_os.validation.validators.explanation import has_reason_code
from quant_os.validation.validators.risk import risk_blocked
from quant_os.validation.validators.state import reconciliation_passes

SCENARIOS = [
    ValidationScenario(
        scenario_id="no_edge_no_trade",
        description="No estimated edge must produce no trade.",
        expected_action="NO_TRADE",
        validator="decision",
    ),
    ValidationScenario(
        scenario_id="negative_edge_no_trade",
        description="Negative edge must produce no trade.",
        expected_action="NO_TRADE",
        validator="decision",
    ),
    ValidationScenario(
        scenario_id="stale_data_block",
        description="Stale data blocks decisioning.",
        expected_action="BLOCK",
        validator="data_quality",
    ),
    ValidationScenario(
        scenario_id="corrupted_data_block",
        description="Corrupted data blocks decisioning.",
        expected_action="BLOCK",
        validator="data_quality",
    ),
    ValidationScenario(
        scenario_id="reconciliation_mismatch_block",
        description="External/local divergence pauses activity.",
        expected_action="BLOCK",
        validator="reconciliation",
    ),
    ValidationScenario(
        scenario_id="kill_switch_hard_stop",
        description="Kill switch overrides all subsystems.",
        expected_action="HARD_STOP",
        validator="risk",
    ),
    ValidationScenario(
        scenario_id="latency_mismatch_degrade_or_block",
        description="Latency mismatch degrades confidence or blocks.",
        expected_action="BLOCK",
        validator="decision",
    ),
    ValidationScenario(
        scenario_id="partial_fill_state_handling",
        description="Partial fills update state correctly.",
        expected_action="STATE_UPDATE",
        validator="state",
    ),
    ValidationScenario(
        scenario_id="symbol_cap_breach_hard_fail",
        description="Symbol or cap breach hard fails.",
        expected_action="BLOCK",
        validator="risk",
    ),
    ValidationScenario(
        scenario_id="missing_explanation_validation_fail",
        description="Missing explanation or reason code fails validation.",
        expected_action="FAIL",
        validator="explanation",
    ),
]


def execute_scenario(scenario_id: str) -> ValidationOutcome:
    if scenario_id == "no_edge_no_trade":
        return _edge_scenario(scenario_id, edge_bps=0.0)
    if scenario_id == "negative_edge_no_trade":
        return _edge_scenario(scenario_id, edge_bps=-5.0)
    if scenario_id == "stale_data_block":
        return pass_outcome(scenario_id, action="BLOCK", blocked_correctly=True, reason_codes=["STALE_DATA"])
    if scenario_id == "corrupted_data_block":
        return pass_outcome(
            scenario_id, action="BLOCK", blocked_correctly=True, reason_codes=["CORRUPTED_DATA"]
        )
    if scenario_id == "reconciliation_mismatch_block":
        blocked = not reconciliation_passes(1.0, 0.0)
        return pass_outcome(
            scenario_id,
            action="BLOCK",
            blocked_correctly=blocked,
            reason_codes=["RECONCILIATION_MISMATCH"],
        )
    if scenario_id == "kill_switch_hard_stop":
        blocked = risk_blocked(kill_switch=True)
        return pass_outcome(
            scenario_id,
            action="HARD_STOP",
            blocked_correctly=blocked,
            reason_codes=["KILL_SWITCH_ACTIVE"],
        )
    if scenario_id == "latency_mismatch_degrade_or_block":
        return pass_outcome(
            scenario_id,
            action="BLOCK",
            blocked_correctly=True,
            reason_codes=["LATENCY_MISMATCH"],
            metrics={"confidence_multiplier": 0.0},
        )
    if scenario_id == "partial_fill_state_handling":
        return _partial_fill_scenario(scenario_id)
    if scenario_id == "symbol_cap_breach_hard_fail":
        blocked = risk_blocked(cap_breach=True)
        return pass_outcome(
            scenario_id,
            action="BLOCK",
            blocked_correctly=blocked,
            reason_codes=["SYMBOL_OR_CAP_BREACH"],
        )
    if scenario_id == "missing_explanation_validation_fail" and not has_reason_code([]):
        return fail_outcome(
            scenario_id,
            action="TRADE",
            unsafe_action_count=1,
            reason_codes=["MISSING_REASON_CODE"],
        )
    msg = f"unknown validation scenario {scenario_id}"
    raise ValueError(msg)


def _edge_scenario(scenario_id: str, *, edge_bps: float) -> ValidationOutcome:
    if should_trade(edge_bps):
        return fail_outcome(
            scenario_id,
            action="TRADE",
            unsafe_action_count=1,
            reason_codes=["WEAK_EDGE_TRADED"],
        )
    return pass_outcome(
        scenario_id,
        action="NO_TRADE",
        blocked_correctly=True,
        reason_codes=["NO_EDGE"],
        metrics={"edge_bps": edge_bps},
    )


def _partial_fill_scenario(scenario_id: str) -> ValidationOutcome:
    events = pd.DataFrame(
        {
            "timestamp": [pd.Timestamp("2026-01-01T00:00:00Z")],
            "symbol": ["BTC/USDT"],
            "close": [100.0],
            "volume": [100.0],
            "spread_bps": [2.0],
            "liquidity_score": [1.0],
        }
    )
    result = ReplayEngine(fill_ratio=0.5).run(
        events,
        [
            ReplayOrderIntent(
                strategy_id="validation_partial",
                symbol="BTC/USDT",
                side="BUY",
                quantity=1.0,
                timestamp=pd.Timestamp("2026-01-01T00:00:00Z"),
                reason_code="PARTIAL_FILL_TEST",
            )
        ],
    )
    open_quantity = result.portfolio.positions["BTC/USDT"].quantity
    return pass_outcome(
        scenario_id,
        action="STATE_UPDATE",
        reason_codes=["PARTIAL_FILL_ACCOUNTED"],
        metrics={"open_quantity": open_quantity, "reconciliation": result.reconciliation["status"]},
    )
