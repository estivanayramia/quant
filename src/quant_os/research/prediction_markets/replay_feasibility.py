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
