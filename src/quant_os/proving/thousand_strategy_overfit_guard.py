from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.research.strategy_factory.campaign_common import safe_payload, write_json_md


def build_thousand_strategy_overfit_guard(
    *,
    attempted_variants: int = 1000,
    top_candidate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    candidate = top_candidate or {}
    blockers = []
    if attempted_variants >= 1000 and not candidate.get("multiple_testing_adjusted", False):
        blockers.append("MULTIPLE_TESTING_PENALTY_REQUIRED")
    if not candidate.get("holdout_passed", False):
        blockers.append("HOLDOUT_OR_FORWARD_WINDOW_NOT_PROVEN")
    if not candidate.get("purged_validation_passed", False):
        blockers.append("PURGED_NO_LEAKAGE_VALIDATION_NOT_PASSED")
    if float(candidate.get("neighbor_parameter_pass_rate", 0.0)) < 0.6:
        blockers.append("NEIGHBORING_PARAMETERS_FAIL_ROBUSTNESS")
    if candidate.get("placebo_survives_similarly", True):
        blockers.append("PLACEBO_SURVIVES_SIMILARLY")
    if not candidate.get("adjusted_performance_significant", False):
        blockers.append("ADJUSTED_PERFORMANCE_NOT_SIGNIFICANT")
    return safe_payload(
        status="OVERFIT_GUARD_PASSED" if not blockers else "OVERFIT_GUARD_BLOCKED",
        attempted_variants=attempted_variants,
        false_discovery_guard="deflated_sharpe_and_familywise_holdout_required",
        probability_of_overfit_warning=bool(blockers),
        blockers=blockers,
        holdout_required=True,
        walk_forward_required=True,
        purged_embargo_required=True,
        family_holdout_required=True,
    )


def write_thousand_strategy_overfit_guard_report(
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    payload = build_thousand_strategy_overfit_guard()
    return write_json_md(
        payload,
        output_root=output_root,
        report_dir="overfit",
        json_name="latest_overfit_guard.json",
        md_name="latest_overfit_guard.md",
        title="Thousand Strategy Overfit Guard",
        lines=[f"Status: {payload['status']}", f"Blockers: {', '.join(payload['blockers'])}"],
    )
