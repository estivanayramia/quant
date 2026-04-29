from __future__ import annotations

from typing import Any

from quant_os.proving.freshness import evaluate_freshness
from quant_os.proving.incident_log import summarize_incidents
from quant_os.proving.stability import compute_strategy_stability
from quant_os.proving.streaks import compute_streaks


def collect_proving_blockers(
    records: list[dict[str, Any]],
    *,
    minimum_successful_runs: int = 14,
) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []
    streaks = compute_streaks(records)
    incidents = summarize_incidents()
    stability = compute_strategy_stability(records)
    freshness = evaluate_freshness()
    if streaks["successful_runs"] < minimum_successful_runs:
        blockers.append("INSUFFICIENT_SUCCESSFUL_RUN_COUNT")
    if incidents["by_severity"].get("CRITICAL", 0) > 0:
        blockers.append("CRITICAL_INCIDENTS_PRESENT")
    if incidents["by_severity"].get("HIGH", 0) > 0:
        blockers.append("HIGH_INCIDENTS_PRESENT")
    if incidents["unresolved_count"] > 0:
        blockers.append("UNRESOLVED_INCIDENTS_PRESENT")
    if freshness["status"] == "FAIL":
        blockers.extend(freshness["failures"])
    elif freshness["status"] == "WARN":
        warnings.extend(freshness["warnings"])
    if stability["status"] == "WARN":
        warnings.extend(stability["warnings"])
    if sum(1 for record in records if record.get("warnings")) >= 3:
        warnings.append("REPEATED_WARNINGS")
    for record in records:
        blockers.extend(str(item) for item in record.get("proving_blockers", []) or [])
    return {
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "streaks": streaks,
        "incidents": incidents,
        "stability": stability,
        "freshness": freshness,
    }
