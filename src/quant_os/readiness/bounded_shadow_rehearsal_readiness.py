from __future__ import annotations

from typing import Any

from quant_os.research.replay_candidates.pm_crypto_updown_dataset_builder import (
    MIN_PRIMARY_REPLAY_READY_ROWS,
)
from quant_os.research.replay_candidates.pm_crypto_updown_policy_replay_eval import (
    MIN_ALLOWED_SHADOW_INTENTS,
)
from quant_os.research.replay_candidates.pm_crypto_updown_schema import CANDIDATE_ID
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

BOUNDED_SHADOW_REHEARSAL_STATUSES = [
    "FILL_REALISM_STILL_BLOCKS_EDGE",
    "NO_CONSERVATIVE_INTENTS_ALLOWED",
    "INTENTS_TOO_THIN_AFTER_FILTERING",
    "BASELINE_OR_PLACEBO_BLOCKED",
    "COST_FILL_BLOCKED",
    "READY_FOR_BOUNDED_SHADOW_REHEARSAL",
    "CANDIDATE_REMAINS_BLOCKED",
]


def evaluate_bounded_shadow_rehearsal_readiness(
    *,
    policy_replay_eval: dict[str, Any],
) -> dict[str, Any]:
    status = _readiness_status(policy_replay_eval)
    ready = status == "READY_FOR_BOUNDED_SHADOW_REHEARSAL"
    return {
        "schema_version": "bounded_shadow_rehearsal_readiness_v1",
        "sequence": "43",
        "candidate_id": CANDIDATE_ID,
        "overall_status": (
            "READY_FOR_BOUNDED_SHADOW_REHEARSAL" if ready else "CANDIDATE_REMAINS_BLOCKED"
        ),
        "readiness_status": status,
        "allowed_statuses": BOUNDED_SHADOW_REHEARSAL_STATUSES,
        "ready_for_bounded_shadow_rehearsal": ready,
        "minimum_primary_replay_ready_rows": MIN_PRIMARY_REPLAY_READY_ROWS,
        "minimum_allowed_shadow_intents": MIN_ALLOWED_SHADOW_INTENTS,
        "primary_evidence_row_count": policy_replay_eval["primary_evidence_row_count"],
        "real_cached_replay_ready_row_count": policy_replay_eval[
            "real_cached_replay_ready_row_count"
        ],
        "allowed_intent_count": policy_replay_eval["allowed_intent_count"],
        "primary_allowed_intent_count": policy_replay_eval["primary_allowed_intent_count"],
        "best_conservative_variant": policy_replay_eval["best_conservative_variant"],
        "baseline_summary": {
            "allowed_intents_beat_baselines": policy_replay_eval[
                "allowed_intents_beat_baselines"
            ],
        },
        "placebo_summary": {
            "allowed_intents_beat_placebos": policy_replay_eval[
                "allowed_intents_beat_placebos"
            ],
        },
        "blockers": _blockers(policy_replay_eval, status),
        "autonomy_milestones": _autonomy_milestones(
            ready=ready,
            policy_replay_eval=policy_replay_eval,
        ),
        "not_live_readiness": True,
        "not_canary_readiness": True,
        "live_readiness_claimed": False,
        "canary_readiness_claimed": False,
        "network_fetch_attempted": False,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _readiness_status(policy_replay_eval: dict[str, Any]) -> str:
    if policy_replay_eval["allowed_intent_count"] <= 0:
        return "NO_CONSERVATIVE_INTENTS_ALLOWED"
    if policy_replay_eval["primary_allowed_intent_count"] < MIN_ALLOWED_SHADOW_INTENTS:
        return "INTENTS_TOO_THIN_AFTER_FILTERING"
    if policy_replay_eval["best_conservative_variant"]["cost_adjusted_result"] <= 0.0:
        return "FILL_REALISM_STILL_BLOCKS_EDGE"
    if policy_replay_eval["primary_evidence_row_count"] < MIN_PRIMARY_REPLAY_READY_ROWS:
        return "COST_FILL_BLOCKED"
    if policy_replay_eval["real_cached_replay_ready_row_count"] <= 0:
        return "CANDIDATE_REMAINS_BLOCKED"
    if (
        not policy_replay_eval["allowed_intents_beat_baselines"]
        or not policy_replay_eval["allowed_intents_beat_placebos"]
    ):
        return "BASELINE_OR_PLACEBO_BLOCKED"
    if policy_replay_eval["synthetic_rows_counted_as_primary"]:
        return "BASELINE_OR_PLACEBO_BLOCKED"
    if policy_replay_eval["policy_answers"]["cost_fill_realism_still_blocks"]:
        return "COST_FILL_BLOCKED"
    return "READY_FOR_BOUNDED_SHADOW_REHEARSAL"


def _blockers(policy_replay_eval: dict[str, Any], status: str) -> list[str]:
    if status == "READY_FOR_BOUNDED_SHADOW_REHEARSAL":
        return []
    blockers = [status]
    if policy_replay_eval["allowed_intent_count"] <= 0:
        blockers.append("ZERO_CONSERVATIVE_SHADOW_INTENTS")
    if policy_replay_eval["primary_allowed_intent_count"] < MIN_ALLOWED_SHADOW_INTENTS:
        blockers.append(
            "PRIMARY_ALLOWED_INTENTS_"
            f"{policy_replay_eval['primary_allowed_intent_count']}_LT_{MIN_ALLOWED_SHADOW_INTENTS}"
        )
    if policy_replay_eval["best_conservative_variant"]["cost_adjusted_result"] <= 0.0:
        blockers.append("CONSERVATIVE_COST_ADJUSTED_RESULT_NON_POSITIVE")
    if policy_replay_eval["primary_evidence_row_count"] < MIN_PRIMARY_REPLAY_READY_ROWS:
        blockers.append(
            "PRIMARY_ROWS_"
            f"{policy_replay_eval['primary_evidence_row_count']}_LT_{MIN_PRIMARY_REPLAY_READY_ROWS}"
        )
    if policy_replay_eval["synthetic_rows_counted_as_primary"]:
        blockers.append("SYNTHETIC_PROOF_INFLATION_BLOCKED")
    return _dedupe(blockers)


def _autonomy_milestones(
    *,
    ready: bool,
    policy_replay_eval: dict[str, Any],
) -> dict[str, str]:
    primary_count = policy_replay_eval["primary_evidence_row_count"]
    real_cached_count = policy_replay_eval["real_cached_replay_ready_row_count"]
    expanded_shadow_complete = primary_count >= MIN_PRIMARY_REPLAY_READY_ROWS
    return {
        "real_cached_evidence_acquisition": (
            "complete" if real_cached_count > 0 else "partial"
        ),
        "replay_threshold": (
            "complete" if primary_count >= MIN_PRIMARY_REPLAY_READY_ROWS else "partial"
        ),
        "expanded_shadow_replay": "complete" if expanded_shadow_complete else "partial",
        "bounded_shadow_rehearsal": "ready" if ready else "blocked",
        "canary": "blocked",
        "live": "blocked",
    }


def _dedupe(items: list[str]) -> list[str]:
    deduped = []
    seen = set()
    for item in items:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped
