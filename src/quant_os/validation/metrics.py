from __future__ import annotations

from typing import Any

from quant_os.validation.contracts import ValidationOutcome


def summarize_validation(outcomes: list[ValidationOutcome]) -> dict[str, Any]:
    unsafe = sum(outcome.unsafe_action_count for outcome in outcomes)
    blocked = sum(1 for outcome in outcomes if outcome.blocked_correctly)
    failed = [outcome.scenario_id for outcome in outcomes if outcome.status != "PASS"]
    return {
        "status": "FAIL" if failed else "PASS",
        "scenario_count": len(outcomes),
        "failed_scenarios": failed,
        "unsafe_action_failure_count": unsafe,
        "blocked_correctly_count": blocked,
        "autonomy_health": {
            "status": "ATTENTION" if unsafe else "HEALTHY",
            "unsafe_action_failure_count": unsafe,
            "blocked_correctly_count": blocked,
            "live_trading_enabled": False,
        },
        "live_trading_enabled": False,
    }
