from __future__ import annotations

from typing import Any

from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY


def evaluate_replay_dataset_readiness(*, dataset_report: dict[str, Any]) -> dict[str, Any]:
    status = _readiness_status(dataset_report)
    ready = status == "REPLAY_DATASET_READY_FOR_CANDIDATE_TEST"
    return {
        "schema_version": "replay_dataset_readiness_v1",
        "sequence": "36",
        "candidate_id": dataset_report["candidate_id"],
        "readiness_status": status,
        "ready_for_phase37_candidate_replay": ready,
        "not_shadow_trading_readiness": True,
        "not_canary_readiness": True,
        "blockers": _readiness_blockers(dataset_report, status),
        "dataset_report_path": dataset_report.get("report_paths", {}).get("json"),
        "row_count": dataset_report["row_count"],
        "replay_ready_row_count": dataset_report["replay_ready_row_count"],
        "clob_coverage": dataset_report["clob_coverage"],
        "spot_coverage": dataset_report["spot_coverage"],
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _readiness_status(dataset_report: dict[str, Any]) -> str:
    if dataset_report["clob_coverage"] == 0.0:
        return "REPLAY_DATASET_BLOCKED_MISSING_CLOB"
    if dataset_report["spot_coverage"] == 0.0:
        return "REPLAY_DATASET_BLOCKED_MISSING_SPOT"
    if dataset_report.get("missing_window_label_count", 0) > 0:
        return "REPLAY_DATASET_BLOCKED_MISSING_WINDOW_LABELS"
    if dataset_report["row_count"] == 0 or dataset_report["replay_ready_row_count"] == 0:
        return "REPLAY_DATASET_BLOCKED_TOO_THIN"
    if (
        dataset_report.get("readiness_status") == "REPLAY_DATASET_READY_FOR_CANDIDATE_TEST"
        and not dataset_report.get("blockers")
    ):
        return "REPLAY_DATASET_READY_FOR_CANDIDATE_TEST"
    return "REPLAY_DATASET_PARTIAL"


def _readiness_blockers(dataset_report: dict[str, Any], status: str) -> list[str]:
    if status == "REPLAY_DATASET_READY_FOR_CANDIDATE_TEST":
        return []
    blockers = list(dataset_report.get("blockers", []))
    if status == "REPLAY_DATASET_BLOCKED_MISSING_CLOB":
        blockers.append("MISSING_CLOB_SNAPSHOT")
    if status == "REPLAY_DATASET_BLOCKED_MISSING_SPOT":
        blockers.append("MISSING_SPOT_SNAPSHOT")
    if status == "REPLAY_DATASET_BLOCKED_MISSING_WINDOW_LABELS":
        blockers.append("MISSING_WINDOW_LABELS")
    if status == "REPLAY_DATASET_BLOCKED_TOO_THIN":
        blockers.append("REPLAY_DATASET_TOO_THIN")
    return sorted(set(blockers))
