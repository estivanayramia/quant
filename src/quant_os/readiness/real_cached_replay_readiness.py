from __future__ import annotations

from typing import Any

from quant_os.research.replay_candidates.pm_crypto_updown_dataset_builder import (
    MIN_PRIMARY_REPLAY_READY_ROWS,
)
from quant_os.research.replay_candidates.pm_crypto_updown_schema import CANDIDATE_ID
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

READINESS_STATUSES = [
    "PRIMARY_EVIDENCE_STILL_TOO_THIN",
    "REAL_CACHED_COVERAGE_TOO_LOW",
    "CLOB_COVERAGE_TOO_LOW",
    "SPOT_COVERAGE_TOO_LOW",
    "LABEL_COVERAGE_TOO_LOW",
    "BASELINE_OR_PLACEBO_BLOCKED",
    "COST_FILL_BLOCKED",
    "READY_FOR_EXPANDED_SHADOW_REPLAY",
]


def evaluate_real_cached_replay_readiness(
    *,
    real_cached_replay_eval: dict[str, Any],
) -> dict[str, Any]:
    status = _readiness_status(real_cached_replay_eval)
    ready = status == "READY_FOR_EXPANDED_SHADOW_REPLAY"
    return {
        "schema_version": "real_cached_replay_readiness_v1",
        "sequence": "39",
        "candidate_id": CANDIDATE_ID,
        "overall_status": (
            "READY_FOR_EXPANDED_SHADOW_REPLAY"
            if ready
            else "CANDIDATE_REMAINS_BLOCKED"
        ),
        "readiness_status": status,
        "allowed_statuses": READINESS_STATUSES,
        "ready_for_expanded_shadow_replay": ready,
        "minimum_primary_replay_ready_rows": MIN_PRIMARY_REPLAY_READY_ROWS,
        "primary_evidence_row_count": real_cached_replay_eval["primary_evidence_row_count"],
        "real_cached_replay_ready_row_count": real_cached_replay_eval[
            "real_cached_replay_ready_row_count"
        ],
        "row_gap": real_cached_replay_eval["row_gap"],
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
        "blockers": _blockers(real_cached_replay_eval, status),
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


def _readiness_status(real_cached_replay_eval: dict[str, Any]) -> str:
    progress = real_cached_replay_eval["threshold_progress"]
    dataset = progress["dataset_report"]
    if real_cached_replay_eval["primary_evidence_row_count"] < MIN_PRIMARY_REPLAY_READY_ROWS:
        return "PRIMARY_EVIDENCE_STILL_TOO_THIN"
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
    if dataset["real_cached_replay_ready_row_count"] <= 0:
        return "REAL_CACHED_COVERAGE_TOO_LOW"
    if not baselines["candidate_beats_market_baseline"] or not baselines["candidate_beats_no_skill"]:
        return "BASELINE_OR_PLACEBO_BLOCKED"
    if not placebos["candidate_beats_placebos_for_readiness"]:
        return "BASELINE_OR_PLACEBO_BLOCKED"
    if costs["costs_destroy_edge"] or fills["fill_realism_blocks_edge"]:
        return "COST_FILL_BLOCKED"
    if real_cached_replay_eval["synthetic_rows_counted_as_primary"]:
        return "BASELINE_OR_PLACEBO_BLOCKED"
    return "READY_FOR_EXPANDED_SHADOW_REPLAY"


def _blockers(real_cached_replay_eval: dict[str, Any], status: str) -> list[str]:
    if status == "READY_FOR_EXPANDED_SHADOW_REPLAY":
        return []
    if status == "PRIMARY_EVIDENCE_STILL_TOO_THIN":
        return [
            f"PRIMARY_ROWS_{real_cached_replay_eval['primary_evidence_row_count']}_LT_"
            f"{MIN_PRIMARY_REPLAY_READY_ROWS}",
            "CANDIDATE_REMAINS_BLOCKED",
        ]
    if status == "REAL_CACHED_COVERAGE_TOO_LOW":
        return ["REAL_CACHED_COVERAGE_TOO_LOW"]
    if status == "CLOB_COVERAGE_TOO_LOW":
        return ["CLOB_COVERAGE_TOO_LOW"]
    if status == "SPOT_COVERAGE_TOO_LOW":
        return ["SPOT_COVERAGE_TOO_LOW"]
    if status == "LABEL_COVERAGE_TOO_LOW":
        return ["LABEL_COVERAGE_TOO_LOW"]
    if status == "COST_FILL_BLOCKED":
        return ["COST_FILL_BLOCKED"]
    return ["BASELINE_OR_PLACEBO_BLOCKED"]


def _autonomy_milestones(*, ready: bool) -> dict[str, str]:
    return {
        "replay_candidate_selected": "complete",
        "replay_data_acquired_aligned": "complete",
        "candidate_replay_tested": "complete",
        "replay_evidence_expansion": "complete",
        "real_cached_evidence_acquisition": "complete" if ready else "partial",
        "expanded_shadow_replay": "ready" if ready else "blocked",
        "canary": "blocked",
        "live": "blocked",
    }
