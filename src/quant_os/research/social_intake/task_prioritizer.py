from __future__ import annotations

from typing import Any

from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY


def prioritize_social_research_tasks(*, hypothesis_queue: dict[str, Any]) -> dict[str, Any]:
    tasks = [_task_from_hypothesis(item) for item in hypothesis_queue["hypotheses"]]
    return {
        "schema_version": "social_research_task_queue_v1",
        "sequence": "34",
        "research_task_queue_status": "PRIORITIZED_SOCIAL_RESEARCH_ONLY",
        "top_priority_reason": "reduce_phase33_thin_evidence_blocker",
        "tasks": sorted(tasks, key=lambda item: (item["priority_rank"], item["task_id"])),
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _task_from_hypothesis(item: dict[str, Any]) -> dict[str, Any]:
    status, rank = _priority(item)
    return {
        "task_id": f"task_{item['hypothesis_id']}",
        "source_post_id": item["source_post_id"],
        "hypothesis_id": item["hypothesis_id"],
        "priority_status": status,
        "priority_rank": rank,
        "relevance_to_current_blockers": _blocker_relevance(item),
        "data_availability": _data_availability(item),
        "replay_feasibility": item["replay_feasibility"],
        "safety": "safe_research_only" if status != "REJECT_UNSAFE" else "unsafe_rejected",
        "expected_value_to_edge_discovery": _edge_value(item),
        "expected_value_to_replay_realism": _replay_value(item),
        "expected_value_to_calibration_validation": _calibration_value(item),
        "cost_time_burden": _cost_burden(item),
        "direct_execution_allowed": False,
        "do_not_trade_directly": True,
    }


def _priority(item: dict[str, Any]) -> tuple[str, int]:
    hypothesis_type = item["hypothesis_type"]
    if hypothesis_type == "unsafe_copy_trade_research":
        return "REJECT_UNSAFE", 90
    if hypothesis_type == "source_candidate":
        return "DO_NOW", 10
    if hypothesis_type in {"benchmark_reference", "macro_hypothesis"}:
        return "DO_NEXT", 20
    if hypothesis_type == "workflow_task":
        return "BACKLOG", 40
    if hypothesis_type == "baseline_calibration_warning":
        return "DO_NEXT", 25
    return "NEEDS_MORE_DATA", 50


def _blocker_relevance(item: dict[str, Any]) -> str:
    if item["hypothesis_type"] in {"source_candidate", "benchmark_reference", "macro_hypothesis"}:
        return "directly_reduces_thin_evidence_or_replay_blocker"
    if item["hypothesis_type"] == "unsafe_copy_trade_research":
        return "safety_filter_only"
    return "indirect_process_or_validation_value"


def _data_availability(item: dict[str, Any]) -> str:
    if item["hypothesis_type"] == "source_candidate":
        return "candidate_source_needs_registry_review"
    if item["replay_feasibility"] == "requires_timestamped_dataset":
        return "needs_timestamped_replay_dataset"
    return "fixture_or_notes_sufficient_for_task"


def _edge_value(item: dict[str, Any]) -> str:
    if item["hypothesis_type"] in {"macro_hypothesis", "source_candidate"}:
        return "medium_if_replayable"
    if item["hypothesis_type"] == "unsafe_copy_trade_research":
        return "none_directly_rejected"
    return "low_or_indirect"


def _replay_value(item: dict[str, Any]) -> str:
    if item["hypothesis_type"] in {"source_candidate", "benchmark_reference"}:
        return "high"
    if item["replay_feasibility"] == "requires_timestamped_dataset":
        return "medium_after_dataset"
    return "low"


def _calibration_value(item: dict[str, Any]) -> str:
    if item["hypothesis_type"] == "baseline_calibration_warning":
        return "high"
    return "baseline_required"


def _cost_burden(item: dict[str, Any]) -> str:
    if item["hypothesis_type"] == "source_candidate":
        return "medium_registry_and_fixture_check"
    if item["replay_feasibility"] == "requires_timestamped_dataset":
        return "high_dataset_build_required"
    return "low"
