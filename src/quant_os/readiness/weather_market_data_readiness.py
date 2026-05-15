from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.data.weather.weather_market_capture_plan import build_weather_market_capture_plan
from quant_os.proving.profit_claim_guard import evaluate_profit_claim_guard
from quant_os.proving.weather_market_paper_proving import run_weather_market_paper_proving
from quant_os.proving.weather_market_paper_report import DEFAULT_FIXTURE_PATH
from quant_os.research.replay_candidates.weather_market_replay_schema import (
    load_weather_market_replay_rows,
)
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

ALLOWED_READINESS_STATUSES = [
    "WEATHER_DATA_CAPTURE_READY",
    "WEATHER_MARKET_DATASET_READY",
    "WEATHER_DATA_CAPTURE_BLOCKED",
    "MARKET_DATA_CAPTURE_BLOCKED",
    "RESOLUTION_LABELS_MISSING",
    "SAMPLE_TOO_THIN",
    "PAPER_PROVING_READY",
    "PAPER_PROFIT_DIAGNOSTIC_ONLY",
    "SELECTED_LANE_NEEDS_MORE_DATA",
    "NO_PROFIT_CLAIM_ALLOWED",
]


def evaluate_weather_market_data_readiness(
    *,
    fixture_path: str | Path = DEFAULT_FIXTURE_PATH,
) -> dict[str, Any]:
    capture_plan = build_weather_market_capture_plan()
    rows = load_weather_market_replay_rows(fixture_path)
    paper = run_weather_market_paper_proving(rows)
    guard = evaluate_profit_claim_guard(paper)
    readiness_status = _readiness_status(capture_plan=capture_plan, paper=paper, guard=guard)
    blockers = _blockers(capture_plan=capture_plan, paper=paper, guard=guard)
    milestones = {
        "profit_lane_selected": "met",
        "paper_proving_harness": "met",
        "weather_data_acquisition": "partial" if rows else "blocked",
        "paper_profit_candidate": "blocked",
        "bounded_shadow_rehearsal": "blocked",
        "canary": "blocked",
        "live": "blocked",
    }
    return {
        "schema_version": "weather_market_data_readiness_v1",
        "sequence": "50",
        "candidate_id": "pm_weather_forecast_market_mismatch",
        "allowed_readiness_statuses": ALLOWED_READINESS_STATUSES,
        "readiness_status": readiness_status,
        "paper_profit_status": guard["claim_status"],
        "blockers": blockers,
        "capture_plan_status": capture_plan["status"],
        "paper_proving_status": paper["readiness_status"],
        "dataset_status": paper["dataset_status"],
        "row_count": paper["row_count"],
        "sample_warnings": paper["sample_warnings"],
        "source_quality_tier": paper["source_quality_tier"],
        "profit_claim_guard": guard,
        "autonomy_milestones": milestones,
        "exact_next_commands": capture_plan["exact_next_commands"],
        "canary_ready": False,
        "live_ready": False,
        "live_readiness_claimed": False,
        "canary_readiness_claimed": False,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _readiness_status(
    *,
    capture_plan: dict[str, Any],
    paper: dict[str, Any],
    guard: dict[str, Any],
) -> str:
    if capture_plan["status"].endswith("NEEDS_OPERATOR_MARKET") and not paper["row_count"]:
        return "MARKET_DATA_CAPTURE_BLOCKED"
    if guard["claim_status"] == "NO_PROFIT_CLAIM_ALLOWED":
        return "PAPER_PROFIT_DIAGNOSTIC_ONLY"
    if "SAMPLE_TOO_THIN" in paper["sample_warnings"]:
        return "SAMPLE_TOO_THIN"
    return "SELECTED_LANE_NEEDS_MORE_DATA"


def _blockers(
    *,
    capture_plan: dict[str, Any],
    paper: dict[str, Any],
    guard: dict[str, Any],
) -> list[str]:
    blockers = []
    if capture_plan["status"].endswith("NEEDS_OPERATOR_MARKET"):
        blockers.append("PUBLIC_WEATHER_MARKET_NOT_SELECTED")
    blockers.extend(guard["blockers"])
    if paper["dataset_status"] == "FIXTURE_ONLY_NOT_PROOF":
        blockers.append("NO_REAL_PUBLIC_DATA")
    return sorted(set(blockers))

