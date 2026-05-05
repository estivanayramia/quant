from __future__ import annotations

from typing import Any


def build_resolution_truth_labels(dataset: dict[str, Any]) -> list[dict[str, Any]]:
    labels = []
    for market in dataset["markets"]:
        resolution = market["resolution"]
        winning_outcome = resolution.get("winning_outcome")
        label_value = _label_value(winning_outcome, resolution.get("status"))
        labels.append(
            {
                "schema_version": "1.0",
                "source": "polymarket",
                "source_mode": dataset["source_mode"],
                "market_id": market["market_id"],
                "condition_id": market["condition_id"],
                "resolution_status": resolution["status"],
                "winning_outcome": winning_outcome,
                "label_value": label_value,
                "label_ready": label_value is not None,
                "resolved_at": resolution.get("resolved_at"),
                "truth_source": resolution.get("truth_source"),
                "uncertainty": resolution.get("confidence") or "UNKNOWN",
                "candidate_research_status": market.get("candidate_research_status"),
                "excluded_from_candidate_research": not market.get(
                    "included_in_candidate_research",
                    False,
                ),
                "exclusion_reason": market.get("exclusion_reason"),
                "join_keys": {
                    "source": "polymarket",
                    "market_id": market["market_id"],
                    "condition_id": market["condition_id"],
                },
                "internet_required": False,
                "label_use": "research_only_prediction_candidate_evaluation",
            }
        )
    return labels


def _label_value(winning_outcome: str | None, status: str | None) -> int | None:
    if status != "RESOLVED":
        return None
    if winning_outcome == "YES":
        return 1
    if winning_outcome == "NO":
        return 0
    return None
