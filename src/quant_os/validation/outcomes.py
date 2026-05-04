from __future__ import annotations

from quant_os.validation.contracts import ValidationOutcome


def pass_outcome(
    scenario_id: str,
    *,
    action: str,
    blocked_correctly: bool = False,
    reason_codes: list[str] | None = None,
    metrics: dict[str, object] | None = None,
) -> ValidationOutcome:
    return ValidationOutcome(
        scenario_id=scenario_id,
        status="PASS",
        action=action,
        blocked_correctly=blocked_correctly,
        reason_codes=reason_codes or [],
        metrics=metrics or {},
    )


def fail_outcome(
    scenario_id: str,
    *,
    action: str,
    unsafe_action_count: int,
    reason_codes: list[str],
    metrics: dict[str, object] | None = None,
) -> ValidationOutcome:
    return ValidationOutcome(
        scenario_id=scenario_id,
        status="FAIL",
        action=action,
        unsafe_action_count=unsafe_action_count,
        reason_codes=reason_codes,
        metrics=metrics or {},
    )
