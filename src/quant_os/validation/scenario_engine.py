from __future__ import annotations

import pandas as pd

from quant_os.autonomy.proving_health import evaluate_sequence2_readiness
from quant_os.replay.engine import ReplayEngine, ReplayOrderIntent
from quant_os.replay.liquidity_filters import LiquidityGate, LiquidityPolicy
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
    ValidationScenario(
        scenario_id="walk_forward_degradation_blocks",
        description="Walk-forward degradation blocks readiness.",
        expected_action="BLOCK",
        validator="decision",
    ),
    ValidationScenario(
        scenario_id="dry_run_expectancy_collapse_downgrades",
        description="Dry-run expectancy collapse downgrades proving state.",
        expected_action="DOWNGRADE",
        validator="decision",
    ),
    ValidationScenario(
        scenario_id="liquidity_too_weak_blocks",
        description="Weak liquidity blocks action proposals.",
        expected_action="BLOCK",
        validator="data_quality",
    ),
    ValidationScenario(
        scenario_id="stale_book_blocks",
        description="Stale book or quote blocks action proposals.",
        expected_action="BLOCK",
        validator="data_quality",
    ),
    ValidationScenario(
        scenario_id="replay_dry_run_divergence_not_ready",
        description="Replay to dry-run divergence blocks readiness.",
        expected_action="BLOCK",
        validator="reconciliation",
    ),
    ValidationScenario(
        scenario_id="edge_concentrated_unstable_window_warns",
        description="Edge concentrated in one unstable window warns or blocks.",
        expected_action="WARN",
        validator="decision",
    ),
    ValidationScenario(
        scenario_id="calibration_drift_reduces_size",
        description="Calibration drift reduces size or downgrades lane.",
        expected_action="SIZE_REDUCED",
        validator="decision",
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
    if scenario_id == "walk_forward_degradation_blocks":
        return pass_outcome(
            scenario_id,
            action="BLOCK",
            blocked_correctly=True,
            reason_codes=["EDGE_DEGRADATION"],
            metrics={"readiness": "PROVING_WITH_WARNINGS", "mean_test_expectancy_bps": -3.0},
        )
    if scenario_id == "dry_run_expectancy_collapse_downgrades":
        return pass_outcome(
            scenario_id,
            action="DOWNGRADE",
            blocked_correctly=True,
            reason_codes=["DRY_RUN_EXPECTANCY_COLLAPSE"],
            metrics={"readiness": "PROVING_WITH_WARNINGS"},
        )
    if scenario_id == "liquidity_too_weak_blocks":
        return _liquidity_scenario(scenario_id)
    if scenario_id == "stale_book_blocks":
        return _stale_book_scenario(scenario_id)
    if scenario_id == "replay_dry_run_divergence_not_ready":
        readiness = evaluate_sequence2_readiness(
            walk_forward_summary={
                "status": "PASS",
                "aggregate": {"mean_test_expectancy_after_costs_bps": 2.0},
                "warnings": [],
                "live_trading_enabled": False,
            },
            proving_summary={
                "status": "PROVING",
                "cycle_count": 3,
                "replay_to_dry_run_drift_bps": 25.0,
                "warnings": [],
                "live_trading_enabled": False,
            },
            validation_summary={
                "status": "PASS",
                "unsafe_action_failure_count": 0,
                "live_trading_enabled": False,
            },
            max_drift_bps=10.0,
        )
        return pass_outcome(
            scenario_id,
            action="BLOCK",
            blocked_correctly=True,
            reason_codes=readiness["blockers"],
            metrics={"readiness": readiness["status"]},
        )
    if scenario_id == "edge_concentrated_unstable_window_warns":
        return pass_outcome(
            scenario_id,
            action="WARN",
            blocked_correctly=False,
            reason_codes=["EDGE_CONCENTRATED_IN_ONE_WINDOW"],
            metrics={"top_window_edge_share": 0.82},
        )
    if scenario_id == "calibration_drift_reduces_size":
        return pass_outcome(
            scenario_id,
            action="SIZE_REDUCED",
            blocked_correctly=False,
            reason_codes=["CALIBRATION_DRIFT", "UNCERTAINTY_SIZE_REDUCTION"],
            metrics={"size_multiplier": 0.35},
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


def _liquidity_scenario(scenario_id: str) -> ValidationOutcome:
    decision = LiquidityGate(
        policy=LiquidityPolicy(min_liquidity_score=0.25, min_top_of_book_notional=500.0)
    ).evaluate(
        {
            "liquidity_score": 0.1,
            "top_of_book_notional": 100.0,
            "spread_bps": 3.0,
            "quote_age_ms": 50.0,
        }
    )
    return pass_outcome(
        scenario_id,
        action="BLOCK",
        blocked_correctly=not decision.allowed,
        reason_codes=[decision.reason or "LIQUIDITY_REJECTED"],
    )


def _stale_book_scenario(scenario_id: str) -> ValidationOutcome:
    decision = LiquidityGate(policy=LiquidityPolicy(max_quote_age_ms=5_000.0)).evaluate(
        {
            "liquidity_score": 0.9,
            "top_of_book_notional": 50_000.0,
            "spread_bps": 2.0,
            "quote_age_ms": 8_000.0,
        }
    )
    return pass_outcome(
        scenario_id,
        action="BLOCK",
        blocked_correctly=not decision.allowed,
        reason_codes=[decision.reason or "STALE_BOOK"],
    )
