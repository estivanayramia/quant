from __future__ import annotations

from typing import Any

REPLAY_FEASIBILITY_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
}

MIN_INCLUDED_MARKETS_FOR_NARROW_REPLAY = 8
MIN_RESOLVED_OBSERVATIONS_FOR_NARROW_REPLAY = 8
MIN_INCLUDED_MARKETS_FOR_SIGNAL_DISCOVERY_REPLAY = 12
MIN_RESOLVED_OBSERVATIONS_FOR_SIGNAL_DISCOVERY_REPLAY = 12
MIN_LANE_ACTIVITY_MARKETS_FOR_REPLAY = 12
MIN_LANE_ACTIVITY_RESOLVED_FOR_REPLAY = 12


def evaluate_replay_feasibility(
    *,
    dataset: dict[str, Any],
    candidate_evaluation: dict[str, Any],
) -> dict[str, Any]:
    blockers = _replay_blockers(dataset=dataset, candidate_evaluation=candidate_evaluation)
    status = _status_from_blockers(blockers)
    return {
        "sequence": "22",
        "source": "polymarket",
        "source_mode": dataset["source_mode"],
        "replay_feasibility_status": status,
        "ready_for_narrow_replay_design": status == "READY_FOR_NARROW_REPLAY_DESIGN",
        "blockers": blockers,
        "dataset_summary": {
            "dataset_id": dataset["dataset_id"],
            "dataset_hash": dataset["dataset_hash"],
            "market_count": dataset["market_count"],
            "included_market_count": dataset["included_market_count"],
            "snapshot_count": dataset["snapshot_count"],
            "resolution_summary": dataset["resolution_summary"],
        },
        "candidate_evaluation_status": candidate_evaluation["candidate_evaluation_status"],
        "candidate_results": candidate_evaluation["candidate_results"],
        "metrics": candidate_evaluation["metrics"],
        "observed_facts": [
            "Replay feasibility uses saved fixture data and deterministic candidate metrics only.",
            "No execution, routing, sizing, signing, wallet mirroring, or live controls are introduced.",
        ],
        "inferred_patterns": [
            "Narrow replay design is blocked when candidate signals do not beat the market baseline.",
        ],
        "unknowns": [
            "Historical fixture depth remains limited and cannot justify autonomous execution.",
            "Replay realism, fill assumptions, fees, and venue mechanics remain unmodeled for prediction markets.",
        ],
        **REPLAY_FEASIBILITY_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def evaluate_replay_preconditions(
    *,
    dataset: dict[str, Any],
    lane_evaluation: dict[str, Any],
) -> dict[str, Any]:
    blockers = _precondition_blockers(dataset=dataset, lane_evaluation=lane_evaluation)
    status = _precondition_status(blockers, lane_evaluation=lane_evaluation)
    return {
        "sequence": "23",
        "source": "polymarket",
        "source_mode": dataset["source_mode"],
        "replay_precondition_status": status,
        "ready_for_narrow_replay_design": status == "READY_FOR_NARROW_REPLAY_DESIGN",
        "blockers": blockers,
        "dataset_summary": {
            "dataset_id": dataset["dataset_id"],
            "dataset_hash": dataset["dataset_hash"],
            "market_count": dataset["market_count"],
            "included_market_count": dataset["included_market_count"],
            "snapshot_count": dataset["snapshot_count"],
            "resolution_summary": dataset["resolution_summary"],
        },
        "best_candidate_lane": lane_evaluation.get("best_lane_evaluation"),
        "lane_evaluation_status": lane_evaluation["lane_evaluation_status"],
        "observed_facts": [
            "Replay preconditions are research-only and use deterministic lane evaluation outputs.",
            "No prediction-market execution, order routing, sizing, signing, or wallet mirroring is enabled.",
        ],
        "inferred_patterns": [
            "A lane can be worth continued research while still being blocked from replay design.",
        ],
        "unknowns": [
            "Replay realism and autonomous execution remain out of scope until a credible signal family exists.",
        ],
        **REPLAY_FEASIBILITY_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def evaluate_lane_replay_readiness(
    *,
    lane_activity_dataset: dict[str, Any],
    lane_evaluation: dict[str, Any],
) -> dict[str, Any]:
    blockers = _lane_replay_readiness_blockers(
        lane_activity_dataset=lane_activity_dataset,
        lane_evaluation=lane_evaluation,
    )
    status = _lane_replay_readiness_status(
        blockers,
        lane_activity_dataset=lane_activity_dataset,
        lane_evaluation=lane_evaluation,
    )
    return {
        "sequence": "24",
        "source": lane_activity_dataset["source"],
        "source_mode": lane_activity_dataset["source_mode"],
        "lane_id": lane_activity_dataset["lane_id"],
        "replay_readiness_status": status,
        "ready_for_narrow_replay_design": status == "READY_FOR_NARROW_REPLAY_DESIGN",
        "blockers": blockers,
        "best_candidate_lane": {
            "lane_id": lane_activity_dataset["lane_id"],
            "lane_name": "Short-Dated Clean Binary",
            "activity_depth_status": lane_activity_dataset["activity_depth_status"],
            "included_market_count": lane_activity_dataset["included_market_count"],
            "resolved_observation_count": lane_evaluation["resolved_observation_count"],
            "best_candidate_signal": lane_evaluation["best_candidate_signal"],
        },
        "dataset_summary": {
            "dataset_id": lane_activity_dataset["dataset_id"],
            "dataset_hash": lane_activity_dataset["dataset_hash"],
            "market_count": lane_activity_dataset["market_count"],
            "included_market_count": lane_activity_dataset["included_market_count"],
            "resolved_market_count": lane_activity_dataset["resolved_market_count"],
            "activity_observation_count": lane_activity_dataset["activity_observation_count"],
            "activity_depth_status": lane_activity_dataset["activity_depth_status"],
        },
        "lane_evaluation_status": lane_evaluation["lane_evaluation_status"],
        "candidate_results": lane_evaluation["candidate_results"],
        "observed_facts": [
            "Replay readiness is research-only and uses saved lane activity fixtures.",
            "No prediction-market execution, routing, sizing, signing, or wallet mirroring is enabled.",
        ],
        "inferred_patterns": [
            "The lane has richer activity history, but replay design remains blocked without a credible baseline-beating signal.",
        ],
        "unknowns": [
            "Replay realism, fees, queue position, fills, and venue mechanics remain unmodeled.",
            "The resolved sample is too small to support autonomous execution readiness.",
        ],
        **REPLAY_FEASIBILITY_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _replay_blockers(
    *,
    dataset: dict[str, Any],
    candidate_evaluation: dict[str, Any],
) -> list[str]:
    blockers = []
    resolved_observations = candidate_evaluation["metrics"]["resolved_observation_count"]
    if dataset["included_market_count"] < MIN_INCLUDED_MARKETS_FOR_NARROW_REPLAY:
        blockers.append("DATASET_TOO_THIN")
    if resolved_observations < MIN_RESOLVED_OBSERVATIONS_FOR_NARROW_REPLAY:
        blockers.append("INSUFFICIENT_RESOLVED_HISTORY")
    if candidate_evaluation["candidate_evaluation_status"] == "BASELINES_NOT_BEATEN":
        blockers.append("BASELINES_NOT_BEATEN")
        blockers.append("SIGNAL_WEAK")
    return blockers


def _precondition_blockers(
    *,
    dataset: dict[str, Any],
    lane_evaluation: dict[str, Any],
) -> list[str]:
    blockers = []
    resolved_count = lane_evaluation["dataset_summary"]["resolution_summary"]["resolved_count"]
    if dataset["included_market_count"] < MIN_INCLUDED_MARKETS_FOR_SIGNAL_DISCOVERY_REPLAY:
        blockers.append("DATASET_TOO_THIN")
    if resolved_count < MIN_RESOLVED_OBSERVATIONS_FOR_SIGNAL_DISCOVERY_REPLAY:
        blockers.append("INSUFFICIENT_RESOLVED_HISTORY")
    if lane_evaluation.get("best_lane_evaluation") is None:
        blockers.append("LANE_TOO_THIN")
        blockers.append("NO_CREDIBLE_SIGNAL_FAMILY")
    if any(lane["lane_status"] == "LANE_TOO_THIN" for lane in lane_evaluation["lane_evaluations"]):
        blockers.append("LANE_TOO_THIN")
    if lane_evaluation["lane_evaluation_status"] == "NO_CREDIBLE_SIGNAL_FAMILY":
        blockers.append("NO_CREDIBLE_SIGNAL_FAMILY")
        blockers.append("BASELINES_NOT_BEATEN")
        blockers.append("SIGNAL_WEAK")
    return _dedupe(blockers)


def _lane_replay_readiness_blockers(
    *,
    lane_activity_dataset: dict[str, Any],
    lane_evaluation: dict[str, Any],
) -> list[str]:
    blockers = []
    if lane_activity_dataset["included_market_count"] < MIN_LANE_ACTIVITY_MARKETS_FOR_REPLAY:
        blockers.append("LANE_TOO_THIN")
    if lane_evaluation["resolved_observation_count"] < MIN_LANE_ACTIVITY_RESOLVED_FOR_REPLAY:
        blockers.append("LANE_TOO_THIN")
    credible = any(
        result["credible_signal_family"] for result in lane_evaluation["candidate_results"].values()
    )
    if not credible:
        blockers.append("NO_CREDIBLE_SIGNAL_FAMILY")
    if lane_evaluation["lane_evaluation_status"] == "BASELINES_NOT_BEATEN":
        blockers.append("BASELINES_NOT_BEATEN")
        blockers.append("SIGNAL_WEAK")
    if lane_evaluation["lane_evaluation_status"] == "SIGNAL_WEAK":
        blockers.append("SIGNAL_WEAK")
    if lane_activity_dataset["activity_depth_status"] != "LANE_ACTIVITY_ENRICHED":
        blockers.append(lane_activity_dataset["activity_depth_status"])
    return _dedupe(blockers)


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    deduped = []
    for item in items:
        if item not in seen:
            deduped.append(item)
            seen.add(item)
    return deduped


def _status_from_blockers(blockers: list[str]) -> str:
    if "DATASET_TOO_THIN" in blockers:
        return "DATASET_TOO_THIN"
    if "INSUFFICIENT_RESOLVED_HISTORY" in blockers:
        return "INSUFFICIENT_RESOLVED_HISTORY"
    if "BASELINES_NOT_BEATEN" in blockers:
        return "REPLAY_NOT_JUSTIFIED"
    if "SIGNAL_WEAK" in blockers:
        return "SIGNAL_WEAK"
    return "READY_FOR_NARROW_REPLAY_DESIGN"


def _precondition_status(blockers: list[str], *, lane_evaluation: dict[str, Any]) -> str:
    if "DATASET_TOO_THIN" in blockers:
        return "DATASET_TOO_THIN"
    if "INSUFFICIENT_RESOLVED_HISTORY" in blockers:
        return "INSUFFICIENT_RESOLVED_HISTORY"
    if lane_evaluation.get("best_lane_evaluation") and "NO_CREDIBLE_SIGNAL_FAMILY" in blockers:
        return "LANE_IDENTIFIED_BUT_REPLAY_NOT_READY"
    if "NO_CREDIBLE_SIGNAL_FAMILY" in blockers:
        return "NO_CREDIBLE_SIGNAL_FAMILY"
    if "BASELINES_NOT_BEATEN" in blockers:
        return "BASELINES_NOT_BEATEN"
    if "SIGNAL_WEAK" in blockers:
        return "SIGNAL_WEAK"
    if "LANE_TOO_THIN" in blockers:
        return "LANE_TOO_THIN"
    return "READY_FOR_NARROW_REPLAY_DESIGN"


def _lane_replay_readiness_status(
    blockers: list[str],
    *,
    lane_activity_dataset: dict[str, Any],
    lane_evaluation: dict[str, Any],
) -> str:
    if not blockers:
        return "READY_FOR_NARROW_REPLAY_DESIGN"
    lane_has_activity_depth = lane_activity_dataset["activity_depth_status"] == "LANE_ACTIVITY_ENRICHED"
    lane_exists = lane_evaluation.get("lane_id") == lane_activity_dataset["lane_id"]
    if lane_exists and lane_has_activity_depth:
        return "LANE_IMPROVED_BUT_REPLAY_NOT_READY"
    if "NO_CREDIBLE_SIGNAL_FAMILY" in blockers:
        return "NO_CREDIBLE_SIGNAL_FAMILY"
    if "BASELINES_NOT_BEATEN" in blockers:
        return "BASELINES_NOT_BEATEN"
    if "SIGNAL_WEAK" in blockers:
        return "SIGNAL_WEAK"
    if "LANE_TOO_THIN" in blockers:
        return "LANE_TOO_THIN"
    return "LANE_IMPROVED_BUT_REPLAY_NOT_READY"
