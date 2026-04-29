from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.data.loaders import load_yaml
from quant_os.proving.blockers import collect_proving_blockers
from quant_os.proving.incident_log import summarize_incidents
from quant_os.proving.run_history import load_proving_history

READINESS_JSON = Path("reports/proving/latest_readiness.json")
READINESS_MD = Path("reports/proving/latest_readiness.md")


def evaluate_proving_readiness(
    records: list[dict[str, Any]] | None = None,
    config_path: str | Path = "configs/proving_mode.yaml",
    write: bool = True,
) -> dict[str, Any]:
    history = records if records is not None else load_proving_history()
    config = load_yaml(config_path) if Path(config_path).exists() else {}
    readiness_config = config.get("readiness", {})
    minimum_runs = int(readiness_config.get("minimum_successful_runs_future", 14))
    blocker_summary = collect_proving_blockers(history, minimum_successful_runs=minimum_runs)
    incidents = summarize_incidents()
    status = _status_from_history(history, blocker_summary, minimum_runs)
    payload = {
        "status": status,
        "readiness_status": status,
        "history_records_count": len(history),
        "minimum_successful_runs_future": minimum_runs,
        "streaks": blocker_summary["streaks"],
        "blockers": blocker_summary["blockers"],
        "warnings": blocker_summary["warnings"],
        "unresolved_incidents": incidents["unresolved_count"],
        "stability": blocker_summary["stability"],
        "freshness": blocker_summary["freshness"],
        "dry_run_proven": status == "DRY_RUN_PROVEN",
        "live_promotion_status": "LIVE_BLOCKED",
        "live_ready": False,
        "live_allowed": False,
        "requires_human_review": bool(readiness_config.get("require_human_review", True)),
    }
    if write:
        _write_readiness(payload)
    return payload


def _status_from_history(
    history: list[dict[str, Any]],
    blocker_summary: dict[str, Any],
    minimum_runs: int,
) -> str:
    if not history:
        return "NOT_STARTED"
    blockers = blocker_summary["blockers"]
    severe = [
        item
        for item in blockers
        if item
        not in {
            "INSUFFICIENT_SUCCESSFUL_RUN_COUNT",
            "UNRESOLVED_INCIDENTS_PRESENT",
        }
    ]
    if severe:
        return "PROVING_UNSTABLE"
    if blocker_summary["incidents"]["by_severity"].get("CRITICAL", 0) > 0:
        return "PROVING_UNSTABLE"
    if blocker_summary["incidents"]["by_severity"].get("HIGH", 0) > 0:
        return "PROVING_UNSTABLE"
    if blocker_summary["streaks"]["successful_runs"] >= minimum_runs:
        return "DRY_RUN_PROVEN"
    if blocker_summary["streaks"]["successful_runs"] > 0:
        return "PROVING_IN_PROGRESS"
    return "INSUFFICIENT_EVIDENCE"


def _write_readiness(payload: dict[str, Any]) -> None:
    READINESS_JSON.parent.mkdir(parents=True, exist_ok=True)
    READINESS_JSON.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8"
    )
    lines = [
        "# Proving Readiness",
        "",
        "Dry-run proving readiness only. No live trading.",
        "",
        f"Readiness: {payload['readiness_status']}",
        f"Dry-run proven: {payload['dry_run_proven']}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Blockers",
    ]
    lines.extend(f"- {item}" for item in (payload["blockers"] or ["None"]))
    lines.extend(["", "## Warnings"])
    lines.extend(f"- {item}" for item in (payload["warnings"] or ["None"]))
    READINESS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
