from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.research.replay_candidates.pm_crypto_updown_allowed_intent_diagnostics import (
    evaluate_pm_crypto_updown_allowed_intent_diagnostics,
)
from quant_os.research.replay_candidates.pm_crypto_updown_baseline_placebo_attribution import (
    evaluate_pm_crypto_updown_baseline_placebo_attribution,
)
from quant_os.research.replay_candidates.pm_crypto_updown_discriminators import (
    evaluate_pm_crypto_updown_discriminators,
)
from quant_os.research.replay_candidates.pm_crypto_updown_overfit_guard import (
    evaluate_pm_crypto_updown_overfit_guard,
)
from quant_os.research.replay_candidates.pm_crypto_updown_policy_replay_eval import (
    MIN_ALLOWED_SHADOW_INTENTS,
)
from quant_os.research.replay_candidates.pm_crypto_updown_retirement import (
    evaluate_pm_crypto_updown_retirement,
)
from quant_os.research.replay_candidates.pm_crypto_updown_schema import CANDIDATE_ID
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

MIN_PRIMARY_ROWS_FOR_BOUNDED_SHADOW = 20
MIN_ALLOWED_REAL_CACHED_INTENTS = 3

CANDIDATE_DECISION_STATUSES = [
    "READY_FOR_BOUNDED_SHADOW_REHEARSAL",
    "NEEDS_MORE_ALLOWED_INTENTS",
    "NEEDS_MORE_REAL_CACHED_EVIDENCE",
    "BASELINE_OR_PLACEBO_BLOCKED",
    "OVERFIT_RISK_TOO_HIGH",
    "DATA_CAPTURE_BLOCKED",
    "CANDIDATE_REMAINS_BLOCKED",
    "DEPRIORITIZE_CANDIDATE",
    "RETIRE_CANDIDATE",
]


def evaluate_pm_crypto_updown_allowed_intent_decision(
    *,
    rows: list[dict[str, Any]] | None = None,
    signal_report: dict[str, Any] | None = None,
    fixture_root: str | Path | None = None,
    real_cached_artifact_roots: list[str | Path] | None = None,
    diagnostics: dict[str, Any] | None = None,
    attribution: dict[str, Any] | None = None,
    overfit_guard: dict[str, Any] | None = None,
    retirement: dict[str, Any] | None = None,
) -> dict[str, Any]:
    diagnostics = diagnostics or evaluate_pm_crypto_updown_allowed_intent_diagnostics(
        rows=rows,
        signal_report=signal_report,
        fixture_root=fixture_root,
        real_cached_artifact_roots=real_cached_artifact_roots,
    )
    if "allowed_primary_rows" in diagnostics and "allowed_primary_signal_report" in diagnostics:
        discriminators = evaluate_pm_crypto_updown_discriminators(diagnostics=diagnostics)
    else:
        discriminators = {
            "schema_version": "pm_crypto_updown_discriminators_v1",
            "sequence": "45",
            "candidate_id": CANDIDATE_ID,
            "input_allowed_primary_count": diagnostics["allowed_primary_intent_count"],
            "discriminators": [],
            "diagnostic_source": "supplied_phase45_decision_inputs",
            **SOCIAL_INTAKE_SAFETY,
            "live_allowed": False,
            "live_promotion_status": "LIVE_BLOCKED",
            "evidence_only": True,
        }
    overfit_guard = overfit_guard or evaluate_pm_crypto_updown_overfit_guard(
        diagnostics=diagnostics,
        discriminator_report=discriminators,
    )
    attribution = attribution or evaluate_pm_crypto_updown_baseline_placebo_attribution(
        diagnostics=diagnostics,
    )
    status = _decision_status(
        diagnostics=diagnostics,
        attribution=attribution,
        overfit_guard=overfit_guard,
        retirement=retirement,
    )
    retirement = retirement or evaluate_pm_crypto_updown_retirement(
        decision_status=status,
        diagnostics=diagnostics,
        attribution=attribution,
    )
    if retirement.get("retirement_action") == "RETIRE_NOW":
        status = "RETIRE_CANDIDATE"
    elif retirement.get("retirement_action") == "DEPRIORITIZE_AND_MONITOR" and status not in {
        "BASELINE_OR_PLACEBO_BLOCKED",
        "OVERFIT_RISK_TOO_HIGH",
    }:
        status = "DEPRIORITIZE_CANDIDATE"
    ready = status == "READY_FOR_BOUNDED_SHADOW_REHEARSAL"
    return {
        "schema_version": "pm_crypto_updown_allowed_intent_decision_v1",
        "sequence": "45",
        "candidate_id": CANDIDATE_ID,
        "decision_status": status,
        "allowed_statuses": CANDIDATE_DECISION_STATUSES,
        "ready_for_bounded_shadow_rehearsal": ready,
        "blockers": _blockers(
            status=status,
            diagnostics=diagnostics,
            attribution=attribution,
            overfit_guard=overfit_guard,
        ),
        "precise_next_action": _next_action(status, diagnostics, retirement),
        "primary_evidence_row_count": diagnostics["primary_evidence_row_count"],
        "minimum_primary_rows_for_bounded_shadow": MIN_PRIMARY_ROWS_FOR_BOUNDED_SHADOW,
        "real_cached_replay_ready_row_count": diagnostics[
            "real_cached_replay_ready_row_count"
        ],
        "allowed_primary_intent_count": diagnostics["allowed_primary_intent_count"],
        "minimum_allowed_primary_intents": MIN_ALLOWED_SHADOW_INTENTS,
        "allowed_real_cached_intent_count": diagnostics["allowed_real_cached_intent_count"],
        "minimum_allowed_real_cached_intents": MIN_ALLOWED_REAL_CACHED_INTENTS,
        "allowed_synthetic_diagnostic_intent_count": diagnostics[
            "allowed_synthetic_diagnostic_intent_count"
        ],
        "candidate_beats_market_baseline": attribution["candidate_beats_market_baseline"],
        "candidate_beats_no_skill_baseline": attribution[
            "candidate_beats_no_skill_baseline"
        ],
        "candidate_beats_or_separates_from_placebos": attribution[
            "candidate_beats_or_separates_from_placebos"
        ],
        "anti_overfit_guard_passes": bool(overfit_guard["passes"]),
        "one_row_dominance_blocked": any(
            item.startswith("ONE_ROW_DOMINANCE_SHARE_")
            for item in overfit_guard.get("blockers", [])
        ),
        "synthetic_rows_counted_as_primary": diagnostics[
            "synthetic_rows_counted_as_primary"
        ],
        "conservative_policy_permits_nonzero_intents": diagnostics[
            "does_any_conservative_policy_allow_nonzero_intents"
        ],
        "diagnostics": diagnostics,
        "discriminators": discriminators,
        "anti_overfit_guard": overfit_guard,
        "baseline_placebo_attribution": attribution,
        "retirement": retirement,
        "autonomy_milestones": {
            "real_cached_evidence_acquisition": "met",
            "replay_threshold": "met",
            "expanded_shadow_replay": "met",
            "allowed_intent_threshold": "met"
            if _allowed_intent_threshold_met(diagnostics)
            else "blocked",
            "bounded_shadow_rehearsal": "ready" if ready else "blocked",
            "canary": "blocked",
            "live": "blocked",
        },
        "not_live_readiness": True,
        "not_canary_readiness": True,
        "live_readiness_claimed": False,
        "canary_readiness_claimed": False,
        "order_routing_enabled": False,
        "order_signing_enabled": False,
        "order_cancellation_enabled": False,
        "wallet_signing_enabled": False,
        "network_fetch_attempted": False,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _decision_status(
    *,
    diagnostics: dict[str, Any],
    attribution: dict[str, Any],
    overfit_guard: dict[str, Any],
    retirement: dict[str, Any] | None,
) -> str:
    if int(diagnostics["allowed_primary_intent_count"]) < MIN_ALLOWED_SHADOW_INTENTS:
        return "NEEDS_MORE_ALLOWED_INTENTS"
    if int(diagnostics["allowed_real_cached_intent_count"]) < MIN_ALLOWED_REAL_CACHED_INTENTS:
        return "NEEDS_MORE_REAL_CACHED_EVIDENCE"
    if int(diagnostics["primary_evidence_row_count"]) < MIN_PRIMARY_ROWS_FOR_BOUNDED_SHADOW:
        return "CANDIDATE_REMAINS_BLOCKED"
    if int(diagnostics["real_cached_replay_ready_row_count"]) < MIN_ALLOWED_REAL_CACHED_INTENTS:
        return "NEEDS_MORE_REAL_CACHED_EVIDENCE"
    if not diagnostics["does_any_conservative_policy_allow_nonzero_intents"]:
        return "CANDIDATE_REMAINS_BLOCKED"
    if float(diagnostics["cost_fill_adjusted_result"]) <= 0.0:
        return "CANDIDATE_REMAINS_BLOCKED"
    if overfit_guard["passes"] is False:
        return "OVERFIT_RISK_TOO_HIGH"
    if attribution["active_blocker"] == "BASELINE_OR_PLACEBO_BLOCKED":
        return "BASELINE_OR_PLACEBO_BLOCKED"
    if not attribution["candidate_beats_market_baseline"]:
        return "BASELINE_OR_PLACEBO_BLOCKED"
    if not attribution["candidate_beats_no_skill_baseline"]:
        return "BASELINE_OR_PLACEBO_BLOCKED"
    if not attribution["candidate_beats_or_separates_from_placebos"]:
        return "BASELINE_OR_PLACEBO_BLOCKED"
    if diagnostics["synthetic_rows_counted_as_primary"]:
        return "OVERFIT_RISK_TOO_HIGH"
    if retirement and retirement.get("retirement_action") == "RETIRE_NOW":
        return "RETIRE_CANDIDATE"
    return "READY_FOR_BOUNDED_SHADOW_REHEARSAL"


def _allowed_intent_threshold_met(diagnostics: dict[str, Any]) -> bool:
    return (
        int(diagnostics["allowed_primary_intent_count"]) >= MIN_ALLOWED_SHADOW_INTENTS
        and int(diagnostics["allowed_real_cached_intent_count"])
        >= MIN_ALLOWED_REAL_CACHED_INTENTS
    )


def _blockers(
    *,
    status: str,
    diagnostics: dict[str, Any],
    attribution: dict[str, Any],
    overfit_guard: dict[str, Any],
) -> list[str]:
    if status == "READY_FOR_BOUNDED_SHADOW_REHEARSAL":
        return []
    blockers = [status]
    if int(diagnostics["allowed_primary_intent_count"]) < MIN_ALLOWED_SHADOW_INTENTS:
        blockers.append(
            "ALLOWED_PRIMARY_INTENTS_"
            f"{diagnostics['allowed_primary_intent_count']}_LT_{MIN_ALLOWED_SHADOW_INTENTS}"
        )
    if int(diagnostics["allowed_real_cached_intent_count"]) < MIN_ALLOWED_REAL_CACHED_INTENTS:
        blockers.append(
            "ALLOWED_REAL_CACHED_INTENTS_"
            f"{diagnostics['allowed_real_cached_intent_count']}_LT_{MIN_ALLOWED_REAL_CACHED_INTENTS}"
        )
    if int(diagnostics["primary_evidence_row_count"]) < MIN_PRIMARY_ROWS_FOR_BOUNDED_SHADOW:
        blockers.append(
            "PRIMARY_ROWS_"
            f"{diagnostics['primary_evidence_row_count']}_LT_{MIN_PRIMARY_ROWS_FOR_BOUNDED_SHADOW}"
        )
    if status == "BASELINE_OR_PLACEBO_BLOCKED":
        blockers.extend(attribution.get("baselines_beating_or_tying_candidate", []))
        blockers.extend(attribution.get("placebos_beating_or_tying_candidate", []))
    if status == "OVERFIT_RISK_TOO_HIGH":
        blockers.extend(overfit_guard["blockers"])
    if status == "CANDIDATE_REMAINS_BLOCKED":
        if not diagnostics["does_any_conservative_policy_allow_nonzero_intents"]:
            blockers.append("NO_CONSERVATIVE_POLICY_INTENTS")
        if float(diagnostics["cost_fill_adjusted_result"]) <= 0.0:
            blockers.append("COST_FILL_ADJUSTED_RESULT_NOT_POSITIVE")
    return _dedupe(blockers)


def _next_action(
    status: str,
    diagnostics: dict[str, Any],
    retirement: dict[str, Any],
) -> str:
    if status == "READY_FOR_BOUNDED_SHADOW_REHEARSAL":
        return "begin_bounded_offline_shadow_rehearsal_without_live_authority"
    if status == "NEEDS_MORE_ALLOWED_INTENTS":
        gap = max(MIN_ALLOWED_SHADOW_INTENTS - int(diagnostics["allowed_primary_intent_count"]), 0)
        return f"collect_at_least_{gap}_more_allowed_primary_intent"
    if status == "NEEDS_MORE_REAL_CACHED_EVIDENCE":
        gap = max(
            MIN_ALLOWED_REAL_CACHED_INTENTS
            - int(diagnostics["allowed_real_cached_intent_count"]),
            0,
        )
        return f"collect_at_least_{gap}_more_allowed_real_cached_intent"
    if status == "BASELINE_OR_PLACEBO_BLOCKED":
        return "do_not_promote_until_candidate_separates_from_baselines_and_placebos"
    if status == "OVERFIT_RISK_TOO_HIGH":
        return "do_not_promote_until_allowed_subset_passes_anti_overfit_guard"
    if status == "DATA_CAPTURE_BLOCKED":
        return "provide_source_policy_approved_read_only_capture_roots"
    if status == "RETIRE_CANDIDATE":
        return "record_retirement_and_stop_candidate_work"
    if status == "DEPRIORITIZE_CANDIDATE":
        return "monitor_only_until_new_evidence_batch_exists"
    return retirement.get("exact_next_data_need", "candidate_remains_blocked_no_shadow_rehearsal")


def _dedupe(items: list[str]) -> list[str]:
    deduped = []
    seen = set()
    for item in items:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped
