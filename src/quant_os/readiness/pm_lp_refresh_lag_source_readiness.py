from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.research.replay_candidates.pm_lp_refresh_lag_schema import (
    ALIASES,
    CANDIDATE_ID,
)
from quant_os.research.replay_candidates.pm_lp_refresh_lag_source_feasibility import (
    AVAILABLE_PUBLIC_READ_ONLY,
    SOURCE_READY_STATUSES,
    build_pm_lp_refresh_lag_source_feasibility,
)
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

ALLOWED_SOURCE_READINESS_STATUSES = [
    "PUBLIC_SOURCE_ACQUISITION_READY",
    "FIRST_REFRESH_LAG_DATASET_READY",
    "BLOCKED_MISSING_PUBLIC_FILL_ATTRIBUTION",
    "BLOCKED_MISSING_QUOTE_REFRESH_TIMESTAMPS",
    "BLOCKED_MISSING_ORDERBOOK_HISTORY",
    "BLOCKED_MISSING_SPOT_TRIGGER_ALIGNMENT",
    "REJECTED_UNSAFE_COPY_TRADE_DEPENDENCY",
]

BASELINE_PLACEBO_FILL_REQUIREMENTS = [
    "no_skill_baseline",
    "stale_quote_random_timestamp_placebo",
    "trigger_sign_flip_placebo",
    "market_mid_holdout_baseline",
    "queue_no_fill_model",
    "partial_fill_sensitivity",
    "adverse_selection_stress",
    "latency_penalty",
]

PUBLIC_SOURCE_SAMPLE_REQUIRED_FIELDS = [
    "market_id",
    "token_id",
    "outcome",
    "event_ts",
    "quote_before",
    "quote_after",
    "quote_refresh_lag_ms",
    "fill_event_ts",
    "stale_side",
    "opposite_side_quote",
    "spot_trigger",
    "taker_burst",
    "spread",
    "liquidity",
    "label_resolution",
    "source_quality",
    "provenance_hash",
]


def evaluate_pm_lp_refresh_lag_source_readiness(
    *,
    field_status_overrides: dict[str, str] | None = None,
    source_feasibility_overrides: dict[str, Any] | None = None,
    fixture_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    feasibility = build_pm_lp_refresh_lag_source_feasibility(
        field_status_overrides=field_status_overrides,
    )
    if source_feasibility_overrides:
        feasibility = {**feasibility, **source_feasibility_overrides}
    statuses = {item["field_id"]: item["status"] for item in feasibility["required_fields"]}
    fixture_validation = (
        validate_pm_lp_refresh_lag_public_source_sample(fixture_payload)
        if fixture_payload is not None
        else _empty_fixture_validation()
    )
    status = _source_readiness_status(
        statuses=statuses,
        unsafe_dependency_flags=feasibility.get("unsafe_dependency_flags", []),
        fixture_validation=fixture_validation,
    )
    missing_fields = _exact_missing_source_fields(status=status, statuses=statuses)
    blockers = (
        []
        if status in {"PUBLIC_SOURCE_ACQUISITION_READY", "FIRST_REFRESH_LAG_DATASET_READY"}
        else [status]
    )
    return {
        "schema_version": "pm_lp_refresh_lag_source_readiness_v1",
        "sequence": "48",
        "candidate_id": CANDIDATE_ID,
        "aliases": ALIASES,
        "allowed_final_statuses": ALLOWED_SOURCE_READINESS_STATUSES,
        "source_readiness_status": status,
        "active_blocker": None if not blockers else blockers[0],
        "blockers": blockers,
        "exact_missing_source_fields": missing_fields,
        "source_feasibility": feasibility,
        "dataset_event_count": fixture_validation["event_count"],
        "blocked_fixture_valid": fixture_validation["blocked_fixture_valid"],
        "fixture_validation": fixture_validation,
        "baseline_placebo_fill_requirements": BASELINE_PLACEBO_FILL_REQUIREMENTS,
        "canary_ready": False,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "autonomy_milestones": _autonomy_milestones(status),
        "exact_next_command": "python -m quant_os.cli data pm-lp-refresh-lag-capture-plan",
        **SOCIAL_INTAKE_SAFETY,
        "evidence_only": True,
    }


def load_pm_lp_refresh_lag_public_source_sample(
    fixture_path: str | Path,
) -> dict[str, Any]:
    import json

    return json.loads(Path(fixture_path).read_text(encoding="utf-8"))


def validate_pm_lp_refresh_lag_public_source_sample(
    payload: dict[str, Any],
) -> dict[str, Any]:
    dataset_status = str(payload.get("dataset_status", ""))
    events = payload.get("events", [])
    if dataset_status in ALLOWED_SOURCE_READINESS_STATUSES and dataset_status.startswith("BLOCKED"):
        missing = payload.get("exact_missing_source_fields", [])
        return {
            "valid": isinstance(events, list) and len(events) == 0 and bool(missing),
            "blocked_fixture_valid": isinstance(events, list)
            and len(events) == 0
            and bool(missing),
            "event_count": 0,
            "missing_event_fields": [],
            "dataset_status": dataset_status,
        }
    missing_by_index = []
    if not isinstance(events, list):
        return {
            "valid": False,
            "blocked_fixture_valid": False,
            "event_count": 0,
            "missing_event_fields": ["events"],
            "dataset_status": dataset_status,
        }
    for index, row in enumerate(events):
        missing = [field for field in PUBLIC_SOURCE_SAMPLE_REQUIRED_FIELDS if field not in row]
        if missing:
            missing_by_index.append({"event_index": index, "missing_fields": missing})
    return {
        "valid": bool(events) and not missing_by_index,
        "blocked_fixture_valid": False,
        "event_count": len(events),
        "missing_event_fields": missing_by_index,
        "dataset_status": dataset_status,
    }


def _source_readiness_status(
    *,
    statuses: dict[str, str],
    unsafe_dependency_flags: list[str],
    fixture_validation: dict[str, Any],
) -> str:
    if unsafe_dependency_flags:
        return "REJECTED_UNSAFE_COPY_TRADE_DEPENDENCY"
    if _missing_fill_attribution(statuses):
        return "BLOCKED_MISSING_PUBLIC_FILL_ATTRIBUTION"
    if statuses["quote_refresh_timestamps"] not in SOURCE_READY_STATUSES:
        return "BLOCKED_MISSING_QUOTE_REFRESH_TIMESTAMPS"
    if statuses["orderbook_snapshots"] not in SOURCE_READY_STATUSES:
        return "BLOCKED_MISSING_ORDERBOOK_HISTORY"
    if statuses["spot_trigger_timestamps"] not in SOURCE_READY_STATUSES:
        return "BLOCKED_MISSING_SPOT_TRIGGER_ALIGNMENT"
    if fixture_validation["valid"] and fixture_validation["event_count"] > 0:
        return "FIRST_REFRESH_LAG_DATASET_READY"
    return "PUBLIC_SOURCE_ACQUISITION_READY"


def _missing_fill_attribution(statuses: dict[str, str]) -> bool:
    return any(
        statuses[field_id] != AVAILABLE_PUBLIC_READ_ONLY
        for field_id in ("maker_taker_role", "maker_wallet_order_attribution")
    )


def _exact_missing_source_fields(*, status: str, statuses: dict[str, str]) -> list[str]:
    if status == "BLOCKED_MISSING_PUBLIC_FILL_ATTRIBUTION":
        return [
            field_id
            for field_id in ("maker_taker_role", "maker_wallet_order_attribution")
            if statuses[field_id] != AVAILABLE_PUBLIC_READ_ONLY
        ]
    if status == "BLOCKED_MISSING_QUOTE_REFRESH_TIMESTAMPS":
        return ["quote_refresh_timestamps"]
    if status == "BLOCKED_MISSING_ORDERBOOK_HISTORY":
        return ["orderbook_snapshots"]
    if status == "BLOCKED_MISSING_SPOT_TRIGGER_ALIGNMENT":
        return ["spot_trigger_timestamps"]
    return []


def _empty_fixture_validation() -> dict[str, Any]:
    return {
        "valid": False,
        "blocked_fixture_valid": False,
        "event_count": 0,
        "missing_event_fields": [],
        "dataset_status": "NO_FIXTURE_PROVIDED",
    }


def _autonomy_milestones(status: str) -> dict[str, str]:
    acquisition = (
        "met"
        if status in {"PUBLIC_SOURCE_ACQUISITION_READY", "FIRST_REFRESH_LAG_DATASET_READY"}
        else "blocked"
    )
    dataset = "met" if status == "FIRST_REFRESH_LAG_DATASET_READY" else "blocked"
    return {
        "phase47_preserved": "met",
        "source_feasibility_review": "met",
        "public_source_acquisition": acquisition,
        "replay_dataset_construction": dataset,
        "bounded_shadow_rehearsal": "blocked",
        "canary": "blocked",
        "live": "blocked",
    }
