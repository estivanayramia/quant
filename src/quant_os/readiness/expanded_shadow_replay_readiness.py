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

SEQUENCE41_READINESS_STATUSES = [
    "PRIMARY_EVIDENCE_STILL_TOO_THIN",
    "REAL_CACHED_COVERAGE_TOO_LOW",
    "CLOB_COVERAGE_TOO_LOW",
    "SPOT_COVERAGE_TOO_LOW",
    "LABEL_COVERAGE_TOO_LOW",
    "BASELINE_OR_PLACEBO_BLOCKED",
    "COST_FILL_BLOCKED",
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


def evaluate_sequence41_expanded_shadow_replay_readiness(
    *,
    real_cached_replay_eval: dict[str, Any],
) -> dict[str, Any]:
    status = _sequence41_readiness_status(real_cached_replay_eval)
    ready = status == "READY_FOR_EXPANDED_SHADOW_REPLAY"
    progress = real_cached_replay_eval["threshold_progress"]
    return {
        "schema_version": "sequence41_expanded_shadow_replay_readiness_v1",
        "sequence": "41",
        "candidate_id": CANDIDATE_ID,
        "overall_status": (
            "READY_FOR_EXPANDED_SHADOW_REPLAY" if ready else "CANDIDATE_REMAINS_BLOCKED"
        ),
        "readiness_status": status,
        "allowed_statuses": SEQUENCE41_READINESS_STATUSES,
        "ready_for_expanded_shadow_replay": ready,
        "minimum_primary_replay_ready_rows": MIN_PRIMARY_REPLAY_READY_ROWS,
        "primary_evidence_row_count": real_cached_replay_eval["primary_evidence_row_count"],
        "real_cached_replay_ready_row_count": real_cached_replay_eval[
            "real_cached_replay_ready_row_count"
        ],
        "row_gap": real_cached_replay_eval["row_gap"],
        "source_coverage": progress["source_coverage"],
        "baseline_summary": {
            "candidate_beats_market_baseline": real_cached_replay_eval["primary_result"][
                "baseline_metrics"
            ]["candidate_beats_market_baseline"],
            "candidate_beats_no_skill": real_cached_replay_eval["primary_result"][
                "baseline_metrics"
            ]["candidate_beats_no_skill"],
        },
        "placebo_summary": {
            "candidate_beats_placebos_for_readiness": real_cached_replay_eval[
                "primary_result"
            ]["placebo_metrics"]["candidate_beats_placebos_for_readiness"],
            "placebo_comparison_status": real_cached_replay_eval["primary_result"][
                "placebo_metrics"
            ]["placebo_comparison_status"],
        },
        "cost_summary": {
            "costs_destroy_edge": real_cached_replay_eval["primary_result"][
                "cost_adjusted_metrics"
            ]["costs_destroy_edge"],
        },
        "fill_summary": {
            "fill_realism_blocks_edge": real_cached_replay_eval["primary_result"][
                "fill_adjusted_metrics"
            ]["fill_realism_blocks_edge"],
        },
        "blockers": _sequence41_blockers(real_cached_replay_eval, status),
        "autonomy_milestones": _sequence41_autonomy_milestones(
            ready=ready,
            real_cached_replay_eval=real_cached_replay_eval,
        ),
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


def _sequence41_readiness_status(real_cached_replay_eval: dict[str, Any]) -> str:
    progress = real_cached_replay_eval["threshold_progress"]
    if real_cached_replay_eval["primary_evidence_row_count"] < MIN_PRIMARY_REPLAY_READY_ROWS:
        return "PRIMARY_EVIDENCE_STILL_TOO_THIN"
    if progress["source_coverage"]["coverage_status"] != "REAL_CACHED_SOURCE_COVERAGE_SUFFICIENT":
        return "REAL_CACHED_COVERAGE_TOO_LOW"
    if real_cached_replay_eval["real_cached_replay_ready_row_count"] <= 0:
        return "REAL_CACHED_COVERAGE_TOO_LOW"
    if progress["source_bottleneck"] == "CLOB/orderbook":
        return "CLOB_COVERAGE_TOO_LOW"
    if progress["source_bottleneck"] == "spot":
        return "SPOT_COVERAGE_TOO_LOW"
    if progress["source_bottleneck"] == "labels/window metadata":
        return "LABEL_COVERAGE_TOO_LOW"
    primary = real_cached_replay_eval["primary_result"]
    baselines = primary["baseline_metrics"]
    placebos = primary["placebo_metrics"]
    costs = primary["cost_adjusted_metrics"]
    fills = primary["fill_adjusted_metrics"]
    if not baselines["candidate_beats_market_baseline"] or not baselines["candidate_beats_no_skill"]:
        return "BASELINE_OR_PLACEBO_BLOCKED"
    if not placebos["candidate_beats_placebos_for_readiness"]:
        return "BASELINE_OR_PLACEBO_BLOCKED"
    if costs["costs_destroy_edge"] or fills["fill_realism_blocks_edge"]:
        return "COST_FILL_BLOCKED"
    if real_cached_replay_eval["synthetic_rows_counted_as_primary"]:
        return "BASELINE_OR_PLACEBO_BLOCKED"
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


def _sequence41_blockers(real_cached_replay_eval: dict[str, Any], status: str) -> list[str]:
    if status == "READY_FOR_EXPANDED_SHADOW_REPLAY":
        return []
    blockers = list(real_cached_replay_eval.get("readiness_blockers", []))
    if status not in blockers:
        blockers.append(status)
    if status == "PRIMARY_EVIDENCE_STILL_TOO_THIN":
        primary_count = real_cached_replay_eval["primary_evidence_row_count"]
        primary_blocker = f"PRIMARY_ROWS_{primary_count}_LT_{MIN_PRIMARY_REPLAY_READY_ROWS}"
        if primary_blocker not in blockers:
            blockers.insert(0, primary_blocker)
        if "CANDIDATE_REMAINS_BLOCKED" not in blockers:
            blockers.append("CANDIDATE_REMAINS_BLOCKED")
    return blockers


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


def _sequence41_autonomy_milestones(
    *,
    ready: bool,
    real_cached_replay_eval: dict[str, Any],
) -> dict[str, str]:
    primary_count = real_cached_replay_eval["primary_evidence_row_count"]
    real_cached_count = real_cached_replay_eval["real_cached_replay_ready_row_count"]
    required_real_cached = real_cached_replay_eval["threshold_progress"]["source_coverage"][
        "required_real_cached_replay_ready_rows"
    ]
    return {
        "replay_candidate_selected": "complete",
        "replay_data_acquired_aligned": "complete",
        "candidate_replay_tested": "complete",
        "real_cached_evidence_acquisition": (
            "complete" if real_cached_count >= required_real_cached and ready else "partial"
        ),
        "replay_evidence_threshold": (
            "complete" if primary_count >= MIN_PRIMARY_REPLAY_READY_ROWS else "partial"
        ),
        "expanded_shadow_replay": "ready" if ready else "blocked",
        "canary": "blocked",
        "live": "blocked",
    }
