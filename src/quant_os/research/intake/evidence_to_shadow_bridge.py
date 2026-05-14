from __future__ import annotations

from typing import Any

from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY


def build_evidence_to_shadow_bridge(*, intake_run: dict[str, Any]) -> dict[str, Any]:
    mappings = [_mapping_for_task(task) for task in intake_run["tasks"]]
    targeted_blockers = sorted(
        {blocker for mapping in mappings for blocker in mapping["blockers_targeted"]}
    )
    return {
        "schema_version": "evidence_to_shadow_bridge_v1",
        "sequence": "35",
        "bridge_status": "MAPPED_RESEARCH_TASKS_TO_SHADOW_BLOCKERS",
        "run_id": intake_run["run_id"],
        "targeted_blockers": targeted_blockers,
        "task_mappings": sorted(mappings, key=lambda item: item["task_id"]),
        "can_reduce_thin_evidence": "BLOCKED_BY_THIN_EVIDENCE" in targeted_blockers,
        "network_fetch_attempted": False,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _mapping_for_task(task: dict[str, Any]) -> dict[str, Any]:
    blockers = _blockers_for_task(task)
    rejected = task["priority_status"] in {"REJECT_UNSAFE", "REJECT_HYPE"}
    return {
        "task_id": task["task_id"],
        "hypothesis_id": task["hypothesis_id"],
        "priority_status": task["priority_status"],
        "blockers_targeted": blockers,
        "required_data": _required_data(task),
        "expected_replay_artifact": _expected_replay_artifact(task),
        "expected_validation_command": _validation_command(task),
        "can_help_shadow_proving": not rejected
        and bool(set(blockers) & {"BLOCKED_BY_THIN_EVIDENCE", "SHADOW_EVIDENCE_TOO_THIN"}),
        "rejected_as_hype_or_unsafe": rejected,
        "next_repo_action": _next_action(task),
        "direct_execution_allowed": False,
        "social_post_trade_signal": False,
    }


def _blockers_for_task(task: dict[str, Any]) -> list[str]:
    priority = task["priority_status"]
    replay = task["replay_feasibility"]
    if priority == "REJECT_UNSAFE":
        return ["SIGNAL_WEAK", "CONFIDENCE_TOO_WEAK"]
    if task["relevance_to_current_blockers"] == "directly_reduces_thin_evidence_or_replay_blocker":
        blockers = ["BLOCKED_BY_THIN_EVIDENCE", "SHADOW_EVIDENCE_TOO_THIN"]
        if replay in {"source_registry_review_required", "benchmark_only"}:
            blockers.append("REPLAY_INPUT_INSUFFICIENT")
        if replay == "requires_timestamped_dataset":
            blockers.append("BASELINES_NOT_BEATEN")
        return blockers
    return ["UNRESOLVED_REALISM_DISQUALIFIER"]


def _required_data(task: dict[str, Any]) -> list[str]:
    if task["priority_status"] == "REJECT_UNSAFE":
        return ["none_direct_execution_rejected"]
    if task["replay_feasibility"] == "requires_timestamped_dataset":
        return ["timestamped_dataset", "out_of_sample_split", "baseline_comparison"]
    if task["replay_feasibility"] == "source_registry_review_required":
        return ["source_registry_review", "coverage_sample", "fixture_schema"]
    return ["fixture_safe_research_note", "replay_design_notes"]


def _expected_replay_artifact(task: dict[str, Any]) -> str:
    if task["priority_status"] == "REJECT_UNSAFE":
        return "unsafe_rejection_record"
    if task["replay_feasibility"] == "requires_timestamped_dataset":
        return "timestamped_replay_dataset_manifest"
    if task["replay_feasibility"] == "source_registry_review_required":
        return "read_only_source_registry_candidate"
    return "fixture_safe_replay_task"


def _validation_command(task: dict[str, Any]) -> str:
    if task["priority_status"] == "REJECT_UNSAFE":
        return ".\\make.cmd sequence34-smoke"
    return ".\\make.cmd sequence35-smoke"


def _next_action(task: dict[str, Any]) -> str:
    if task["priority_status"] == "REJECT_UNSAFE":
        return "keep_rejected_and_do_not_promote"
    if task["priority_status"] == "DO_NOW":
        return "build_read_only_source_fixture_and_registry_review"
    if task["priority_status"] == "DO_NEXT":
        return "convert_to_timestamped_replay_task"
    return "keep_in_research_backlog_until_data_exists"
