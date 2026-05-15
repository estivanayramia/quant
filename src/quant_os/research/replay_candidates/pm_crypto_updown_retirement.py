from __future__ import annotations

from typing import Any

from quant_os.research.replay_candidates.pm_crypto_updown_policy_replay_eval import (
    MIN_ALLOWED_SHADOW_INTENTS,
)
from quant_os.research.replay_candidates.pm_crypto_updown_schema import CANDIDATE_ID
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY


def evaluate_pm_crypto_updown_retirement(
    *,
    decision_status: str,
    diagnostics: dict[str, Any],
    attribution: dict[str, Any],
) -> dict[str, Any]:
    action = _action(
        decision_status=decision_status,
        diagnostics=diagnostics,
        attribution=attribution,
    )
    return {
        "schema_version": "pm_crypto_updown_retirement_v1",
        "sequence": "44",
        "candidate_id": CANDIDATE_ID,
        "decision_status": decision_status,
        "retirement_action": action,
        "auto_retired": action == "RETIRE_NOW",
        "exact_next_data_need": _next_data_need(
            action=action,
            diagnostics=diagnostics,
        ),
        "network_fetch_attempted": False,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _action(
    *,
    decision_status: str,
    diagnostics: dict[str, Any],
    attribution: dict[str, Any],
) -> str:
    if decision_status == "READY_FOR_BOUNDED_SHADOW_REHEARSAL":
        return "CONTINUE_TO_SHADOW_REHEARSAL"
    if decision_status == "RETIRE_CANDIDATE":
        return "RETIRE_NOW"
    if decision_status == "DEPRIORITIZE_CANDIDATE":
        return "DEPRIORITIZE_AND_MONITOR"
    if attribution.get("candidate_needs_more_data_or_retirement") == "RETIRE_CANDIDATE":
        return "DEPRIORITIZE_AND_MONITOR"
    if int(diagnostics.get("allowed_primary_intent_count", 0)) < MIN_ALLOWED_SHADOW_INTENTS:
        return "CONTINUE_WITH_MORE_ALLOWED_INTENTS"
    if decision_status in {"BASELINE_OR_PLACEBO_BLOCKED", "OVERFIT_RISK_TOO_HIGH"}:
        return "DEPRIORITIZE_AND_MONITOR"
    return "CONTINUE_WITH_MORE_ALLOWED_INTENTS"


def _next_data_need(*, action: str, diagnostics: dict[str, Any]) -> str:
    if action == "CONTINUE_TO_SHADOW_REHEARSAL":
        return "none_candidate_gate_passed"
    if action == "RETIRE_NOW":
        return "none_candidate_retired"
    if action == "DEPRIORITIZE_AND_MONITOR":
        return "monitor_only_until_new_allowed_primary_evidence_batch_exists"
    gap = max(MIN_ALLOWED_SHADOW_INTENTS - int(diagnostics.get("allowed_primary_intent_count", 0)), 0)
    return f"collect_at_least_{gap}_more_allowed_primary_intent"
