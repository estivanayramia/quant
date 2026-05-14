from __future__ import annotations

from typing import Any

from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY
from quant_os.research.social_intake.source_candidate_bridge import (
    propose_read_only_source_candidates,
)


def build_evidence_acquisition_plan(*, task_queue: dict[str, Any]) -> dict[str, Any]:
    tasks = task_queue["tasks"]
    worth_testing = [
        _worth_testing_record(task)
        for task in tasks
        if task["priority_status"] in {"DO_NOW", "DO_NEXT", "NEEDS_MORE_DATA"}
    ]
    rejected = [
        task["source_post_id"]
        for task in tasks
        if task["priority_status"] in {"REJECT_UNSAFE", "REJECT_HYPE"}
    ]
    return {
        "schema_version": "social_evidence_acquisition_plan_v1",
        "sequence": "34",
        "evidence_plan_status": "PLAN_REDUCES_THIN_EVIDENCE_WITHOUT_SOCIAL_SIGNALS",
        "phase33_blocker_addressed": "BLOCKED_BY_THIN_EVIDENCE",
        "data_needed": [
            "timestamped_replay_datasets",
            "source_coverage_samples",
            "out_of_sample_splits",
            "baseline_comparison_results",
        ],
        "replay_improvements_needed": [
            "more_real_or_fixture_quality_windows",
            "resolution_timing_alignment",
            "orderbook_depth_and_fill_uncertainty_notes",
        ],
        "source_candidates": [
            "source_registry_candidate_review",
            *[
                proposal["candidate_id"]
                for proposal in propose_read_only_source_candidates(tasks=task_queue)
            ],
        ],
        "source_candidate_proposals": propose_read_only_source_candidates(tasks=task_queue),
        "social_capture_improvements": [
            "preserve_manifest_text_json_html_notes",
            "preserve_post_url_author_capture_timestamp",
            "hash_raw_text_for_provenance",
            "record_missing_optional_files",
        ],
        "hypotheses_worth_testing": worth_testing,
        "hypotheses_rejected": rejected,
        "explicit_avoidances": [
            "no_live_trading",
            "no_social_posts_as_signals",
            "no_following_people_or_wallets",
            "no_unreplayable_macro_claims",
        ],
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _worth_testing_record(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": task["task_id"],
        "source_post_id": task["source_post_id"],
        "priority_status": task["priority_status"],
        "relevance_to_current_blockers": task["relevance_to_current_blockers"],
        "required_next_step": _next_step(task),
        "direct_execution_allowed": False,
    }


def _next_step(task: dict[str, Any]) -> str:
    if task["priority_status"] == "DO_NOW":
        return "source_registry_candidate_review"
    if task["replay_feasibility"] == "requires_timestamped_dataset":
        return "build_timestamped_replay_dataset_fixture"
    return "write_research_spec_and_fixture_safe_replay_task"
