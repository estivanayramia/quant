from __future__ import annotations

from typing import Any

from quant_os.research.replay_candidates.pm_crypto_updown_schema import CANDIDATE_ID
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

MIN_REPLAY_READY_ROWS_FOR_EXPANDED_SHADOW = 20

READINESS_STATUSES = [
    "CANDIDATE_REPLAY_TOO_THIN",
    "BASELINES_NOT_BEATEN",
    "PLACEBO_NOT_BEATEN",
    "COSTS_DESTROY_EDGE",
    "FILL_REALISM_BLOCKS_EDGE",
    "CANDIDATE_REPLAY_BLOCKED",
    "CANDIDATE_REPLAY_PROMISING_BUT_NEEDS_MORE_DATA",
    "READY_FOR_EXPANDED_SHADOW_REPLAY",
]


def evaluate_candidate_replay_readiness(*, evaluation_report: dict[str, Any]) -> dict[str, Any]:
    status = _readiness_status(evaluation_report)
    ready = status == "READY_FOR_EXPANDED_SHADOW_REPLAY"
    return {
        "schema_version": "candidate_replay_readiness_v1",
        "sequence": "37",
        "candidate_id": CANDIDATE_ID,
        "readiness_status": status,
        "allowed_statuses": READINESS_STATUSES,
        "ready_for_expanded_shadow_replay": ready,
        "not_live_readiness": True,
        "not_canary_readiness": True,
        "live_readiness_claimed": False,
        "canary_readiness_claimed": False,
        "blockers": _blockers(evaluation_report, status),
        "row_count": evaluation_report["row_count"],
        "replay_ready_row_count": evaluation_report["replay_ready_row_count"],
        "primary_evidence_row_count": evaluation_report["primary_evidence_row_count"],
        "candidate_signal_count": evaluation_report["candidate_signal_count"],
        "baseline_summary": {
            "candidate_beats_market_baseline": evaluation_report["baseline_metrics"][
                "candidate_beats_market_baseline"
            ],
            "candidate_beats_no_skill": evaluation_report["baseline_metrics"][
                "candidate_beats_no_skill"
            ],
        },
        "placebo_summary": {
            "candidate_beats_placebos_for_readiness": evaluation_report["placebo_metrics"][
                "candidate_beats_placebos_for_readiness"
            ],
            "placebo_comparison_status": evaluation_report["placebo_metrics"][
                "placebo_comparison_status"
            ],
        },
        "cost_summary": {
            "costs_destroy_edge": evaluation_report["cost_adjusted_metrics"][
                "costs_destroy_edge"
            ],
            "cost_adjusted_score": evaluation_report["cost_adjusted_metrics"][
                "cost_adjusted_score"
            ],
        },
        "fill_summary": {
            "fill_realism_blocks_edge": evaluation_report["fill_adjusted_metrics"][
                "fill_realism_blocks_edge"
            ],
            "fill_adjusted_score": evaluation_report["fill_adjusted_metrics"][
                "fill_adjusted_score"
            ],
        },
        "confidence_warnings": evaluation_report["confidence_warnings"],
        "autonomy_milestones": _autonomy_milestones(status),
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _readiness_status(evaluation_report: dict[str, Any]) -> str:
    if evaluation_report["primary_evidence_row_count"] < MIN_REPLAY_READY_ROWS_FOR_EXPANDED_SHADOW:
        return "CANDIDATE_REPLAY_TOO_THIN"
    baselines = evaluation_report["baseline_metrics"]
    if not baselines["candidate_beats_market_baseline"] or not baselines["candidate_beats_no_skill"]:
        return "BASELINES_NOT_BEATEN"
    if not evaluation_report["placebo_metrics"]["candidate_beats_placebos_for_readiness"]:
        return "PLACEBO_NOT_BEATEN"
    if evaluation_report["cost_adjusted_metrics"]["costs_destroy_edge"]:
        return "COSTS_DESTROY_EDGE"
    if evaluation_report["fill_adjusted_metrics"]["fill_realism_blocks_edge"]:
        return "FILL_REALISM_BLOCKS_EDGE"
    if evaluation_report["candidate_signal_count"] == 0:
        return "CANDIDATE_REPLAY_BLOCKED"
    if evaluation_report["primary_evidence_row_count"] < 50:
        return "CANDIDATE_REPLAY_PROMISING_BUT_NEEDS_MORE_DATA"
    return "READY_FOR_EXPANDED_SHADOW_REPLAY"


def _blockers(evaluation_report: dict[str, Any], status: str) -> list[str]:
    if status == "READY_FOR_EXPANDED_SHADOW_REPLAY":
        return []
    if status == "CANDIDATE_REPLAY_TOO_THIN":
        return [
            "REPLAY_READY_ROWS_TOO_THIN",
            f"PRIMARY_ROWS_{evaluation_report['primary_evidence_row_count']}_LT_"
            f"{MIN_REPLAY_READY_ROWS_FOR_EXPANDED_SHADOW}",
        ]
    if status == "BASELINES_NOT_BEATEN":
        return ["BASELINES_NOT_BEATEN"]
    if status == "PLACEBO_NOT_BEATEN":
        return ["PLACEBO_NOT_BEATEN"]
    if status == "COSTS_DESTROY_EDGE":
        return ["COSTS_DESTROY_EDGE"]
    if status == "FILL_REALISM_BLOCKS_EDGE":
        return ["FILL_REALISM_BLOCKS_EDGE"]
    if status == "CANDIDATE_REPLAY_BLOCKED":
        return ["NO_QUALIFYING_CANDIDATE_SIGNALS"]
    return ["NEEDS_MORE_DATA_BEFORE_EXPANDED_SHADOW_REPLAY"]


def _autonomy_milestones(status: str) -> dict[str, str]:
    expanded = (
        "ready" if status == "READY_FOR_EXPANDED_SHADOW_REPLAY" else "blocked"
    )
    return {
        "replay_candidate_selected": "complete",
        "replay_data_acquired_aligned": "complete",
        "candidate_replay_tested": "complete",
        "expanded_shadow_replay": expanded,
        "shadow_canary_live": "blocked",
    }
