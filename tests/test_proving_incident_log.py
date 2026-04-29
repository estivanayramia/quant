from __future__ import annotations

from quant_os.proving.incident_log import append_incidents, create_incident, incidents_for_record


def test_incident_log_records_incidents(local_project) -> None:
    incident = create_incident(
        severity="CRITICAL",
        source="test",
        category="LIVE_DANGER_EVIDENCE",
        summary="dry_run false detected",
    )
    summary = append_incidents([incident])
    assert summary["incidents_count"] == 1
    assert summary["by_severity"]["CRITICAL"] == 1


def test_record_blocker_creates_incident() -> None:
    incidents = incidents_for_record(
        {
            "run_id": "run_x",
            "run_status": "completed",
            "proving_blockers": ["DATASET_QUALITY_FAILED"],
        }
    )
    assert incidents
    assert incidents[0]["category"] == "DATA_QUALITY_FAILURE"
