from __future__ import annotations

from typing import Any

from quant_os.research.replay_candidates.pm_crypto_updown_policy_replay_eval import (
    MIN_ALLOWED_SHADOW_INTENTS,
)
from quant_os.research.replay_candidates.pm_crypto_updown_schema import CANDIDATE_ID
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

PHASE46_FINAL_STATUSES = [
    "READY_FOR_BOUNDED_SHADOW_REHEARSAL",
    "NEEDS_MORE_ALLOWED_INTENTS",
    "DEPRIORITIZE_CANDIDATE",
    "RETIRE_CANDIDATE",
]
MIN_ALLOWED_REAL_CACHED_INTENTS = 3


def evaluate_pm_crypto_updown_phase46_candidate_path(
    *,
    capture_pass: dict[str, Any],
    candidate_decision: dict[str, Any],
) -> dict[str, Any]:
    final_status = _final_status(capture_pass=capture_pass, candidate_decision=candidate_decision)
    ready = final_status == "READY_FOR_BOUNDED_SHADOW_REHEARSAL"
    handoff = final_status in {"DEPRIORITIZE_CANDIDATE", "RETIRE_CANDIDATE"}
    return {
        "schema_version": "pm_crypto_updown_phase46_candidate_path_v1",
        "sequence": "46",
        "candidate_id": CANDIDATE_ID,
        "allowed_final_statuses": PHASE46_FINAL_STATUSES,
        "final_status": final_status,
        "ready_for_bounded_shadow_rehearsal": ready,
        "bounded_shadow_rehearsal_package_created": ready,
        "next_candidate_handoff_created": handoff,
        "blockers": _blockers(capture_pass=capture_pass, candidate_decision=candidate_decision),
        "exact_next_command": _exact_next_command(
            final_status=final_status,
            capture_pass=capture_pass,
        ),
        "capture_pass": capture_pass,
        "candidate_decision": candidate_decision,
        "allowed_primary_intents_before": int(capture_pass["allowed_primary_intents_before"]),
        "allowed_primary_intents_after": int(capture_pass["allowed_primary_intents_after"]),
        "allowed_real_cached_intents_before": int(
            capture_pass["allowed_real_cached_intents_before"]
        ),
        "allowed_real_cached_intents_after": int(capture_pass["allowed_real_cached_intents_after"]),
        "candidate_beats_market_baseline": bool(
            candidate_decision.get("candidate_beats_market_baseline", False)
        ),
        "candidate_beats_no_skill_baseline": bool(
            candidate_decision.get("candidate_beats_no_skill_baseline", False)
        ),
        "candidate_beats_or_separates_from_placebos": bool(
            candidate_decision.get("candidate_beats_or_separates_from_placebos", False)
        ),
        "anti_overfit_guard_passes": bool(
            candidate_decision.get("anti_overfit_guard_passes", False)
        ),
        "autonomy_milestones": {
            "phase45_preserved": "met",
            "phase46_capture_pass": "attempted"
            if capture_pass.get("capture_attempted")
            else "blocked",
            "allowed_intent_threshold": "met"
            if capture_pass.get("allowed_intent_threshold_passed")
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
        "network_fetch_attempted": bool(capture_pass.get("network_attempted", False)),
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _final_status(*, capture_pass: dict[str, Any], candidate_decision: dict[str, Any]) -> str:
    if candidate_decision.get("decision_status") == "RETIRE_CANDIDATE":
        return "RETIRE_CANDIDATE"
    if _ready(capture_pass=capture_pass, candidate_decision=candidate_decision):
        return "READY_FOR_BOUNDED_SHADOW_REHEARSAL"
    if _manifest_only_no_improvement(capture_pass):
        return "DEPRIORITIZE_CANDIDATE"
    if capture_pass.get("capture_attempted") is False and capture_pass.get(
        "exact_next_command_if_still_blocked"
    ):
        return "NEEDS_MORE_ALLOWED_INTENTS"
    if not capture_pass.get("allowed_intent_threshold_passed", False):
        if not capture_pass.get("capture_attempted", False):
            return "NEEDS_MORE_ALLOWED_INTENTS"
        return "DEPRIORITIZE_CANDIDATE"
    if not candidate_decision.get("ready_for_bounded_shadow_rehearsal", False):
        return "DEPRIORITIZE_CANDIDATE"
    return "DEPRIORITIZE_CANDIDATE"


def _ready(*, capture_pass: dict[str, Any], candidate_decision: dict[str, Any]) -> bool:
    return (
        int(capture_pass["allowed_primary_intents_after"]) >= MIN_ALLOWED_SHADOW_INTENTS
        and int(capture_pass["allowed_real_cached_intents_after"]) >= MIN_ALLOWED_REAL_CACHED_INTENTS
        and bool(capture_pass.get("allowed_intent_threshold_passed", False))
        and candidate_decision.get("decision_status") == "READY_FOR_BOUNDED_SHADOW_REHEARSAL"
        and bool(candidate_decision.get("ready_for_bounded_shadow_rehearsal", False))
        and bool(candidate_decision.get("candidate_beats_market_baseline", False))
        and bool(candidate_decision.get("candidate_beats_no_skill_baseline", False))
        and bool(candidate_decision.get("candidate_beats_or_separates_from_placebos", False))
        and bool(candidate_decision.get("anti_overfit_guard_passes", False))
    )


def _manifest_only_no_improvement(capture_pass: dict[str, Any]) -> bool:
    return (
        bool(capture_pass.get("capture_attempted", False))
        and int(capture_pass.get("artifacts_accepted", 0)) == 0
        and int(capture_pass.get("rows_imported", 0)) == 0
        and int(capture_pass["allowed_primary_intents_after"])
        <= int(capture_pass["allowed_primary_intents_before"])
        and int(capture_pass["allowed_real_cached_intents_after"])
        <= int(capture_pass["allowed_real_cached_intents_before"])
    )


def _blockers(
    *,
    capture_pass: dict[str, Any],
    candidate_decision: dict[str, Any],
) -> list[str]:
    if _ready(capture_pass=capture_pass, candidate_decision=candidate_decision):
        return []
    blockers = list(candidate_decision.get("blockers", []))
    if int(capture_pass["allowed_primary_intents_after"]) < MIN_ALLOWED_SHADOW_INTENTS:
        blockers.append(
            "ALLOWED_PRIMARY_INTENTS_"
            f"{capture_pass['allowed_primary_intents_after']}_LT_{MIN_ALLOWED_SHADOW_INTENTS}"
        )
    if int(capture_pass["allowed_real_cached_intents_after"]) < MIN_ALLOWED_REAL_CACHED_INTENTS:
        blockers.append(
            "ALLOWED_REAL_CACHED_INTENTS_"
            f"{capture_pass['allowed_real_cached_intents_after']}_LT_{MIN_ALLOWED_REAL_CACHED_INTENTS}"
        )
    if _manifest_only_no_improvement(capture_pass):
        blockers.append("MANIFEST_ONLY_CAPTURE_PASS_NO_ALLOWED_INTENT_IMPROVEMENT")
    if not candidate_decision.get("candidate_beats_or_separates_from_placebos", False):
        blockers.append("BASELINE_OR_PLACEBO_BLOCKED")
    if not candidate_decision.get("anti_overfit_guard_passes", False):
        blockers.append("ANTI_OVERFIT_GUARD_BLOCKED")
    return _dedupe(blockers)


def _exact_next_command(*, final_status: str, capture_pass: dict[str, Any]) -> str:
    if final_status == "READY_FOR_BOUNDED_SHADOW_REHEARSAL":
        return "python -m quant_os.cli proving pm-crypto-updown-bounded-shadow-rehearsal-spec"
    if final_status == "NEEDS_MORE_ALLOWED_INTENTS":
        return str(capture_pass.get("exact_next_command_if_still_blocked", ""))
    if final_status in {"DEPRIORITIZE_CANDIDATE", "RETIRE_CANDIDATE"}:
        return "git switch main && git pull --ff-only && git switch -c phase-47-pm-lp-refresh-lag-arbitrage"
    return ""


def _dedupe(items: list[str]) -> list[str]:
    deduped = []
    seen = set()
    for item in items:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped
