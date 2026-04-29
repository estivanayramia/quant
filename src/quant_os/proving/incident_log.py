from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from quant_os.core.ids import deterministic_id
from quant_os.proving.run_record import PROVING_ROOT

INCIDENTS_JSON = PROVING_ROOT / "latest_incidents.json"
INCIDENTS_MD = PROVING_ROOT / "latest_incidents.md"
LIVE_DANGER_TERMS = ("LIVE_TRADING", "DRY_RUN_FALSE", "LIVE_DANGER", "KEY_DETECTED")


def create_incident(
    *,
    severity: str,
    source: str,
    category: str,
    summary: str,
    details: dict[str, Any] | None = None,
    related_run_id: str | None = None,
    related_strategy_id: str | None = None,
    related_artifact: str | None = None,
) -> dict[str, Any]:
    timestamp = datetime.now(UTC).isoformat()
    incident_id = deterministic_id(
        "incident", timestamp, severity, source, category, summary, length=20
    )
    return {
        "incident_id": incident_id,
        "timestamp": timestamp,
        "severity": severity,
        "source": source,
        "category": category,
        "summary": summary,
        "details": details or {},
        "related_run_id": related_run_id,
        "related_strategy_id": related_strategy_id,
        "related_artifact": related_artifact,
        "resolved": False,
        "resolution_note": None,
    }


def incidents_for_record(record: dict[str, Any]) -> list[dict[str, Any]]:
    incidents: list[dict[str, Any]] = []
    run_id = record.get("run_id")
    if record.get("run_status") != "completed":
        incidents.append(
            create_incident(
                severity="HIGH",
                source="proving",
                category="RUNBOOK_FAILURE",
                summary="Autonomous run did not complete",
                details={"run_status": record.get("run_status")},
                related_run_id=run_id,
            )
        )
    for blocker in record.get("proving_blockers", []):
        incidents.append(
            create_incident(
                severity=_severity_for_blocker(blocker),
                source="proving",
                category=_category_for_blocker(blocker),
                summary=str(blocker),
                details={"blocker": blocker},
                related_run_id=run_id,
            )
        )
    return incidents


def append_incidents(incidents: list[dict[str, Any]]) -> dict[str, Any]:
    existing = load_incidents()
    seen = {item["incident_id"] for item in existing}
    merged = existing + [item for item in incidents if item["incident_id"] not in seen]
    _write_incidents(merged)
    return summarize_incidents(merged)


def load_incidents() -> list[dict[str, Any]]:
    if not INCIDENTS_JSON.exists():
        return []
    try:
        payload = json.loads(INCIDENTS_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return list(payload.get("incidents", []))


def summarize_incidents(incidents: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    items = incidents if incidents is not None else load_incidents()
    unresolved = [item for item in items if not item.get("resolved")]
    by_severity: dict[str, int] = {}
    for item in unresolved:
        by_severity[item["severity"]] = by_severity.get(item["severity"], 0) + 1
    return {
        "status": "PASS" if not unresolved else "WARN",
        "incidents_count": len(items),
        "unresolved_count": len(unresolved),
        "by_severity": by_severity,
        "incidents": items,
        "live_promotion_status": "LIVE_BLOCKED",
    }


def _write_incidents(incidents: list[dict[str, Any]]) -> None:
    PROVING_ROOT.mkdir(parents=True, exist_ok=True)
    summary = summarize_incidents(incidents)
    INCIDENTS_JSON.write_text(
        json.dumps(summary, indent=2, sort_keys=True, default=str), encoding="utf-8"
    )
    lines = [
        "# Proving Incidents",
        "",
        "Incident history for dry-run/simulation proving only. No live trading.",
        "",
        f"Unresolved incidents: {summary['unresolved_count']}",
        "",
        "## Incidents",
    ]
    if incidents:
        lines.extend(
            f"- {item['severity']} {item['category']}: {item['summary']}"
            for item in incidents
        )
    else:
        lines.append("- None")
    INCIDENTS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _severity_for_blocker(blocker: str) -> str:
    upper = blocker.upper()
    if any(term in upper for term in LIVE_DANGER_TERMS):
        return "CRITICAL"
    if "FAIL" in upper or "FAILED" in upper:
        return "HIGH"
    return "MEDIUM"


def _category_for_blocker(blocker: str) -> str:
    upper = blocker.upper()
    if any(term in upper for term in LIVE_DANGER_TERMS):
        return "LIVE_DANGER_EVIDENCE"
    if "LEAKAGE" in upper:
        return "LEAKAGE_FAILURE"
    if "QUALITY" in upper:
        return "DATA_QUALITY_FAILURE"
    if "DRIFT" in upper:
        return "DRIFT_FAILURE"
    if "RECONCILIATION" in upper:
        return "RECONCILIATION_FAILURE"
    return "UNKNOWN_ERROR"
