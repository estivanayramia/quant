from __future__ import annotations

from enum import StrEnum
from typing import Any

EXPECTED_ADVERSARIAL_VALIDATION_FAILURES = {"missing_explanation_validation_fail"}


class Sequence2ReadinessStatus(StrEnum):
    NOT_READY = "NOT_READY"
    PROVING = "PROVING"
    PROVING_WITH_WARNINGS = "PROVING_WITH_WARNINGS"
    CONDITIONALLY_READY_FOR_TINY_MANUAL_CANARY = "CONDITIONALLY_READY_FOR_TINY_MANUAL_CANARY"
    BLOCKED = "BLOCKED"


def evaluate_sequence2_readiness(
    *,
    walk_forward_summary: dict[str, Any] | None = None,
    proving_summary: dict[str, Any] | None = None,
    validation_summary: dict[str, Any] | None = None,
    realism_summary: dict[str, Any] | None = None,
    min_cycles_for_conditional: int = 3,
    min_oos_expectancy_bps: float = 0.0,
    max_drift_bps: float = 10.0,
) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []

    if walk_forward_summary is None:
        blockers.append("MISSING_WALK_FORWARD_EVIDENCE")
    if proving_summary is None:
        blockers.append("MISSING_DRY_RUN_PROVING_EVIDENCE")
    if validation_summary is None:
        blockers.append("MISSING_VALIDATION_EVIDENCE")
    if realism_summary is None:
        blockers.append("MISSING_REPLAY_REALISM_EVIDENCE")

    for name, summary in [
        ("walk_forward", walk_forward_summary),
        ("proving", proving_summary),
        ("validation", validation_summary),
        ("realism", realism_summary),
    ]:
        if summary and bool(summary.get("live_trading_enabled")):
            blockers.append(f"{name.upper()}:LIVE_TRADING_ENABLED")

    if validation_summary:
        failed = {
            str(item)
            for item in validation_summary.get("failed_scenarios", [])
            if item is not None
        }
        unexpected_failed = failed - EXPECTED_ADVERSARIAL_VALIDATION_FAILURES
        unsafe = int(validation_summary.get("unsafe_action_failure_count", 0))
        expected_unsafe = len(failed & EXPECTED_ADVERSARIAL_VALIDATION_FAILURES)
        if failed & EXPECTED_ADVERSARIAL_VALIDATION_FAILURES:
            warnings.append("EXPECTED_ADVERSARIAL_VALIDATION_FAILURE_CAUGHT")
        if unexpected_failed or unsafe > expected_unsafe:
            blockers.append("VALIDATION_UNSAFE_ACTIONS_PRESENT")

    oos_expectancy = None
    if walk_forward_summary:
        warnings.extend(str(item) for item in walk_forward_summary.get("warnings", []))
        aggregate = walk_forward_summary.get("aggregate", {})
        oos_expectancy = float(aggregate.get("mean_test_expectancy_after_costs_bps", 0.0))
        if oos_expectancy < min_oos_expectancy_bps:
            warnings.append("EDGE_DEGRADATION")

    cycle_count = 0
    if proving_summary:
        warnings.extend(str(item) for item in proving_summary.get("warnings", []))
        blockers.extend(str(item) for item in proving_summary.get("blockers", []))
        if proving_summary.get("status") == Sequence2ReadinessStatus.BLOCKED.value:
            blockers.append("DRY_RUN_PROVING_BLOCKED")
        cycle_count = int(proving_summary.get("cycle_count", 0))
        drift = float(proving_summary.get("replay_to_dry_run_drift_bps", 0.0))
        if drift > max_drift_bps:
            blockers.append("REPLAY_DRY_RUN_DRIFT_TOO_HIGH")

    if realism_summary:
        blockers.extend(str(item) for item in realism_summary.get("blockers", []))
        warnings.extend(str(item) for item in realism_summary.get("warnings", []))

    blockers = sorted(set(blockers))
    warnings = sorted(set(warnings))
    status = _status(blockers, warnings, cycle_count, min_cycles_for_conditional)
    return {
        "status": status.value,
        "readiness_status": status.value,
        "blockers": blockers,
        "warnings": warnings,
        "cycle_count": cycle_count,
        "oos_expectancy_after_costs_bps": oos_expectancy,
        "live_allowed": False,
        "live_trading_enabled": False,
        "live_promotion_status": "LIVE_BLOCKED",
    }


def _status(
    blockers: list[str],
    warnings: list[str],
    cycle_count: int,
    min_cycles_for_conditional: int,
) -> Sequence2ReadinessStatus:
    missing = [item for item in blockers if item.startswith("MISSING_")]
    if missing:
        return Sequence2ReadinessStatus.NOT_READY
    if blockers:
        return Sequence2ReadinessStatus.BLOCKED
    if warnings:
        return Sequence2ReadinessStatus.PROVING_WITH_WARNINGS
    if cycle_count >= min_cycles_for_conditional:
        return Sequence2ReadinessStatus.CONDITIONALLY_READY_FOR_TINY_MANUAL_CANARY
    return Sequence2ReadinessStatus.PROVING
