from __future__ import annotations

from typing import Any


def incident_metric_summary(incidents: list[dict[str, Any]]) -> dict[str, Any]:
    unresolved = [item for item in incidents if not item.get("resolved")]
    return {
        "incidents_count": len(incidents),
        "unresolved_count": len(unresolved),
        "critical_count": sum(1 for item in unresolved if item.get("severity") == "CRITICAL"),
        "high_count": sum(1 for item in unresolved if item.get("severity") == "HIGH"),
    }
