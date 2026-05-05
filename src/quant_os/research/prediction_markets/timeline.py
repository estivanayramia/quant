from __future__ import annotations

from typing import Any


def build_market_lifecycle_timelines(dataset: dict[str, Any]) -> list[dict[str, Any]]:
    timelines = []
    for market in dataset["markets"]:
        snapshots = market.get("snapshots") or []
        statuses = []
        if market.get("opened_at"):
            statuses.append({"timestamp": market["opened_at"], "lifecycle_status": "OPENED"})
        statuses.extend(
            {
                "timestamp": snapshot["timestamp"],
                "lifecycle_status": snapshot["lifecycle_status"],
            }
            for snapshot in snapshots
        )
        if market.get("end_time"):
            statuses.append({"timestamp": market["end_time"], "lifecycle_status": "CLOSED"})
        if market["resolution"]["status"] == "RESOLVED":
            statuses.append(
                {
                    "timestamp": market["resolution"]["resolved_at"],
                    "lifecycle_status": "RESOLVED",
                }
            )
        timelines.append(
            {
                "market_id": market["market_id"],
                "condition_id": market["condition_id"],
                "resolution_status": market["resolution"]["status"],
                "candidate_research_status": market.get("candidate_research_status"),
                "exclusion_reason": market.get("exclusion_reason"),
                "snapshot_count": len(snapshots),
                "statuses": statuses,
                "lifecycle_summary": _lifecycle_summary(statuses),
                "internet_required": False,
            }
        )
    return timelines


def _lifecycle_summary(statuses: list[dict[str, Any]]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for status in statuses:
        lifecycle_status = str(status["lifecycle_status"])
        summary[lifecycle_status] = summary.get(lifecycle_status, 0) + 1
    return summary
