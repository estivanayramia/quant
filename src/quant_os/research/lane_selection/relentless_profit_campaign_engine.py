from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from quant_os.research.lane_selection.relentless_profit_campaign_models import (
    CAMPAIGN_CHECKPOINTED_NOT_COMPLETE,
    CAMPAIGN_SAFETY,
    CONTINUE_TO_NEXT_LANE,
    FORBIDDEN_COMPLETION_STATUSES,
    NEEDS_FORWARD_DATA_CAPTURE,
    PAPER_PROFIT_CANDIDATE_FOUND,
    build_initial_lane_universe,
    default_expansion_candidates,
)


def score_campaign_lanes(lanes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scored = []
    for lane in lanes:
        safety_score = _safety_score(lane)
        proof_score = _proof_score(lane)
        score = int(lane.get("priority", 0)) + safety_score + proof_score
        if lane.get("research_only") or not lane.get("promotion_allowed", True):
            score -= 35
        scored.append(
            {
                **deepcopy(lane),
                "score": max(score, 0),
                "safety_score": safety_score,
                "proof_score": proof_score,
            }
        )
    return sorted(scored, key=lambda item: (-int(item["score"]), str(item["lane_id"])))


def select_next_lane(
    lanes: list[dict[str, Any]],
    state: dict[str, Any],
) -> dict[str, Any] | None:
    attempted = set(state.get("lanes_attempted", []))
    signatures = state.get("lane_blocker_signatures", {})
    for lane in score_campaign_lanes(lanes):
        lane_id = str(lane["lane_id"])
        blocker_signature = str(lane.get("blocker_signature", ""))
        if lane_id in attempted and signatures.get(lane_id) == blocker_signature:
            continue
        return lane
    return None


def attempt_lane(
    lane: dict[str, Any],
    *,
    public_network_ok: bool = False,
) -> dict[str, Any]:
    lane = deepcopy(lane)
    lane_id = str(lane["lane_id"])
    blockers = _unsafe_blockers(lane)
    status = CONTINUE_TO_NEXT_LANE
    proof_rows_created = 0
    source_policy = lane.get("source_policy", "public_read_only_no_auth_no_paid_api")

    if lane.get("research_only") or not lane.get("promotion_allowed", True):
        blockers.insert(0, "RESEARCH_ONLY_LANE_CANNOT_PROMOTE")
    elif lane_id == "pm_weather_forecast_market_mismatch":
        status = NEEDS_FORWARD_DATA_CAPTURE
        blockers.append("HISTORICAL_FORECAST_SNAPSHOTS_MISSING")
        blockers.append("NO_LOOKAHEAD_FORECAST_ARCHIVE_NOT_AVAILABLE_IN_REPO")
    elif lane_id == "pm_weather_historical_forecast_archive_mismatch":
        status = NEEDS_FORWARD_DATA_CAPTURE
        blockers.append("HISTORICAL_FORECAST_ARCHIVE_NOT_CAPTURED")
        blockers.append("SOURCE_TERMS_AND_ISSUE_TIME_POLICY_REVIEW_REQUIRED")
    elif lane_id == "pm_weather_bucket_boundary_mispricing":
        status = NEEDS_FORWARD_DATA_CAPTURE
        blockers.append("HISTORICAL_FORECAST_SNAPSHOTS_MISSING")
        blockers.append("WEATHER_BUCKET_BOUNDARY_REPLAY_MISSING")
    elif lane.get("structural_relation_required"):
        blockers.append("VALIDATED_SEMANTIC_RELATION_MISSING")
        blockers.append("ORDERBOOK_REPLAY_MISSING")
        blockers.append("RESOLUTION_LABEL_PATH_MISSING")
    elif lane.get("family") == "crypto_spot":
        blockers.append("PUBLIC_SPOT_REPLAY_DATASET_MISSING")
        blockers.append("WALK_FORWARD_DATASET_MISSING")
        blockers.append("COST_SPREAD_FILL_REPLAY_MISSING")
    elif lane.get("family") == "equity_etf_paper":
        blockers.append("PUBLIC_EQUITY_REPLAY_DATASET_MISSING")
        blockers.append("BENCHMARK_AND_PLACEBO_REPLAY_MISSING")
    else:
        blockers.append(str(lane.get("blocker_signature", "PUBLIC_REPLAY_DATASET_MISSING")))

    blockers = _dedupe(blockers)
    if lane_id.startswith("pm_weather") and not public_network_ok:
        capture_status = "PUBLIC_NETWORK_DISABLED_FIXTURE_SAFE"
    elif public_network_ok:
        capture_status = "PUBLIC_READ_ONLY_CAPTURE_NOT_IMPLEMENTED_FOR_LANE"
    else:
        capture_status = "NO_NETWORK_NEEDED_FOR_BLOCKER_RECORD"
    return {
        "lane_id": lane_id,
        "family": lane.get("family"),
        "status": status,
        "promotion_allowed": bool(lane.get("promotion_allowed", True)) and not lane.get("research_only", False),
        "paper_profit_candidate": False,
        "paper_status": CAMPAIGN_CHECKPOINTED_NOT_COMPLETE,
        "profit_claim_status": "NO_PROFIT_CLAIM_ALLOWED",
        "blockers": blockers,
        "blocker_signature": str(lane.get("blocker_signature", blockers[0] if blockers else "")),
        "proof_rows_created": proof_rows_created,
        "source_policy": source_policy,
        "capture_status": capture_status,
        "public_network_ok": public_network_ok,
        "reproducible_commands": [
            "python -m quant_os.cli proving relentless-profit-campaign-run"
        ],
        "live_ready": False,
        "canary_ready": False,
        **CAMPAIGN_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def expand_safe_lane_queue(
    candidates: list[dict[str, Any]] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    added = []
    rejected = []
    for candidate in deepcopy(candidates or default_expansion_candidates()):
        blockers = _unsafe_blockers(candidate)
        if not candidate.get("public_data_available", True):
            blockers.append("PUBLIC_DATA_UNAVAILABLE")
        if blockers:
            candidate["blockers"] = _dedupe(blockers)
            candidate["promotion_allowed"] = False
            rejected.append(candidate)
        else:
            candidate.setdefault("promotion_allowed", True)
            candidate.setdefault("research_only", False)
            candidate.setdefault("paper_only", True)
            candidate.setdefault("blocker_signature", "PUBLIC_REPLAY_DATASET_MISSING")
            candidate.setdefault("source_policy", "public_read_only_no_auth_no_paid_api")
            candidate.update(CAMPAIGN_SAFETY)
            added.append(candidate)
    return {"added": added, "rejected": rejected}


def validate_weather_forecast_inputs(row: dict[str, Any]) -> dict[str, Any]:
    blockers = []
    source = str(row.get("forecast_source", "")).lower()
    if row.get("uses_resolution_as_forecast") is True or "realized" in source or "resolution" in source:
        blockers.append("REALIZED_WEATHER_CANNOT_BE_FORECAST")
    forecast_ts = _parse_ts(str(row.get("forecast_ts", "")))
    orderbook_ts = _parse_ts(str(row.get("orderbook_ts", "")))
    if forecast_ts is None or orderbook_ts is None:
        blockers.append("FORECAST_OR_ORDERBOOK_TIMESTAMP_INVALID")
    elif forecast_ts > orderbook_ts:
        blockers.append("FORECAST_AFTER_ORDERBOOK")
    return {"valid": not blockers, "blockers": blockers}


def is_campaign_complete_status(status: str) -> bool:
    return status == PAPER_PROFIT_CANDIDATE_FOUND and status not in FORBIDDEN_COMPLETION_STATUSES


def build_campaign_queue(
    state: dict[str, Any],
    *,
    lanes: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    queued = lanes or build_initial_lane_universe()
    queued = [*queued, *list(state.get("lanes_added_during_expansion", []))]
    return score_campaign_lanes(queued)


def should_expand_queue(lanes: list[dict[str, Any]], state: dict[str, Any]) -> bool:
    return select_next_lane(lanes, state) is None


def _safety_score(lane: dict[str, Any]) -> int:
    score = 0
    safe_flags = [
        not lane.get("requires_private_auth", False),
        not lane.get("requires_wallet_or_signing", False),
        not lane.get("requires_live_execution", False),
        not lane.get("requires_paid_api", False),
        not lane.get("requires_evasion", False),
        not lane.get("requires_futures_or_margin", False),
        not lane.get("requires_leverage", False),
        not lane.get("requires_options", False),
        not lane.get("copy_trade_dependency", False),
    ]
    score += sum(3 for flag in safe_flags if flag)
    if lane.get("paper_only", False):
        score += 4
    if lane.get("spot_only", False):
        score += 3
    return score


def _proof_score(lane: dict[str, Any]) -> int:
    fields = [
        "public_data_available",
        "replayable",
        "timestamped",
        "baseline_testable",
        "placebo_testable",
        "cost_fill_model_possible",
    ]
    return sum(4 for field in fields if lane.get(field, False))


def _unsafe_blockers(lane: dict[str, Any]) -> list[str]:
    blockers = []
    if lane.get("requires_private_auth"):
        blockers.append("PRIVATE_OR_AUTHENTICATED_SOURCE_REQUIRED")
    if lane.get("requires_wallet_or_signing"):
        blockers.append("WALLET_OR_SIGNING_REQUIRED")
    if lane.get("requires_live_execution"):
        blockers.append("LIVE_EXECUTION_REQUIRED")
    if lane.get("requires_paid_api"):
        blockers.append("PAID_API_REQUIRED")
    if lane.get("requires_evasion"):
        blockers.append("ANTI_BOT_OR_PROXY_EVASION_REQUIRED")
    if lane.get("requires_futures_or_margin") or lane.get("requires_leverage") or lane.get("requires_options"):
        blockers.append("FUTURES_LEVERAGE_OR_MARGIN_OUT_OF_SCOPE")
    if lane.get("copy_trade_dependency"):
        blockers.append("COPY_TRADE_DEPENDENCY_FORBIDDEN")
    if lane.get("on_chain_execution_risk"):
        blockers.append("ON_CHAIN_EXECUTION_RISK")
    return blockers


def _parse_ts(value: str) -> datetime | None:
    try:
        if not value.endswith("Z"):
            return None
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo != UTC:
        return None
    return parsed


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result
