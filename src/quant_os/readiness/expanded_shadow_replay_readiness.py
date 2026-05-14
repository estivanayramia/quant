from __future__ import annotations

from typing import Any

from quant_os.research.replay_candidates.pm_crypto_updown_dataset_builder import (
    MIN_PRIMARY_REPLAY_READY_ROWS,
)
from quant_os.research.replay_candidates.pm_crypto_updown_schema import CANDIDATE_ID
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

READINESS_STATUSES = [
    "EXPANDED_SHADOW_REPLAY_NOT_READY",
    "PRIMARY_EVIDENCE_TOO_THIN",
    "CLOB_COVERAGE_TOO_LOW",
    "SPOT_COVERAGE_TOO_LOW",
    "LABEL_COVERAGE_TOO_LOW",
    "PLACEBO_OR_BASELINE_BLOCKED",
    "READY_FOR_EXPANDED_SHADOW_REPLAY",
]


def evaluate_expanded_shadow_replay_readiness(
    *,
    expanded_replay_eval: dict[str, Any],
) -> dict[str, Any]:
    status = _readiness_status(expanded_replay_eval)
    ready = status == "READY_FOR_EXPANDED_SHADOW_REPLAY"
    blockers = _blockers(expanded_replay_eval, status)
    return {
        "schema_version": "expanded_shadow_replay_readiness_v1",
        "sequence": "38",
        "candidate_id": CANDIDATE_ID,
        "overall_status": (
            "READY_FOR_EXPANDED_SHADOW_REPLAY"
            if ready
            else "EXPANDED_SHADOW_REPLAY_NOT_READY"
        ),
        "readiness_status": status,
        "allowed_statuses": READINESS_STATUSES,
        "ready_for_expanded_shadow_replay": ready,
        "minimum_primary_replay_ready_rows": MIN_PRIMARY_REPLAY_READY_ROWS,
        "primary_evidence_row_count": expanded_replay_eval["primary_evidence_row_count"],
        "replay_ready_row_count": expanded_replay_eval["replay_ready_row_count"],
        "source_mix": expanded_replay_eval["evidence_quality"]["source_quality_counts"],
        "baseline_summary": {
            "candidate_beats_market_baseline": expanded_replay_eval["primary_result"][
                "baseline_metrics"
            ]["candidate_beats_market_baseline"],
            "candidate_beats_no_skill": expanded_replay_eval["primary_result"][
                "baseline_metrics"
            ]["candidate_beats_no_skill"],
        },
        "placebo_summary": {
            "candidate_beats_placebos_for_readiness": expanded_replay_eval["primary_result"][
                "placebo_metrics"
            ]["candidate_beats_placebos_for_readiness"],
            "placebo_comparison_status": expanded_replay_eval["primary_result"][
                "placebo_metrics"
            ]["placebo_comparison_status"],
        },
        "cost_summary": {
            "costs_destroy_edge": expanded_replay_eval["primary_result"][
                "cost_adjusted_metrics"
            ]["costs_destroy_edge"],
        },
        "fill_summary": {
            "fill_realism_blocks_edge": expanded_replay_eval["primary_result"][
                "fill_adjusted_metrics"
            ]["fill_realism_blocks_edge"],
        },
        "blockers": blockers,
        "autonomy_milestones": _autonomy_milestones(ready=ready),
        "not_live_readiness": True,
        "not_canary_readiness": True,
        "live_readiness_claimed": False,
        "canary_readiness_claimed": False,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _readiness_status(expanded_replay_eval: dict[str, Any]) -> str:
    quality = expanded_replay_eval["evidence_quality"]
    if quality["primary_evidence_row_count"] < MIN_PRIMARY_REPLAY_READY_ROWS:
        return "PRIMARY_EVIDENCE_TOO_THIN"
    if quality["clob_coverage"] < 1.0:
        return "CLOB_COVERAGE_TOO_LOW"
    if quality["spot_coverage"] < 1.0:
        return "SPOT_COVERAGE_TOO_LOW"
    if quality["label_count"] == 0:
        return "LABEL_COVERAGE_TOO_LOW"
    primary = expanded_replay_eval["primary_result"]
    baselines = primary["baseline_metrics"]
    placebos = primary["placebo_metrics"]
    costs = primary["cost_adjusted_metrics"]
    fills = primary["fill_adjusted_metrics"]
    if not baselines["candidate_beats_market_baseline"] or not baselines["candidate_beats_no_skill"]:
        return "PLACEBO_OR_BASELINE_BLOCKED"
    if not placebos["candidate_beats_placebos_for_readiness"]:
        return "PLACEBO_OR_BASELINE_BLOCKED"
    if costs["costs_destroy_edge"] or fills["fill_realism_blocks_edge"]:
        return "PLACEBO_OR_BASELINE_BLOCKED"
    if expanded_replay_eval["synthetic_rows_counted_as_primary"]:
        return "PLACEBO_OR_BASELINE_BLOCKED"
    return "READY_FOR_EXPANDED_SHADOW_REPLAY"


def _blockers(expanded_replay_eval: dict[str, Any], status: str) -> list[str]:
    quality = expanded_replay_eval["evidence_quality"]
    if status == "READY_FOR_EXPANDED_SHADOW_REPLAY":
        return []
    if status == "PRIMARY_EVIDENCE_TOO_THIN":
        return [
            f"PRIMARY_ROWS_{quality['primary_evidence_row_count']}_LT_"
            f"{MIN_PRIMARY_REPLAY_READY_ROWS}",
            "CANDIDATE_REMAINS_BLOCKED",
        ]
    if status == "CLOB_COVERAGE_TOO_LOW":
        return ["CLOB_COVERAGE_TOO_LOW"]
    if status == "SPOT_COVERAGE_TOO_LOW":
        return ["SPOT_COVERAGE_TOO_LOW"]
    if status == "LABEL_COVERAGE_TOO_LOW":
        return ["LABEL_COVERAGE_TOO_LOW"]
    return ["PLACEBO_OR_BASELINE_BLOCKED"]


def _autonomy_milestones(*, ready: bool) -> dict[str, str]:
    return {
        "replay_candidate_selected": "complete",
        "replay_data_acquired_aligned": "partial",
        "candidate_replay_tested": "complete",
        "replay_evidence_expansion": "complete" if ready else "partial",
        "expanded_shadow_replay": "ready" if ready else "blocked",
        "shadow_rehearsal": "blocked",
        "canary": "blocked",
        "live": "blocked",
    }
