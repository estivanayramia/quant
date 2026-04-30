from __future__ import annotations

from pathlib import Path

from quant_os.canary.incident_drill import build_incident_drill


def test_incident_drill_and_rollback_reports_generated(local_project):
    payload = build_incident_drill()
    assert payload["status"] == "PLANNING_ONLY"
    assert len(payload["scenarios"]) >= 3
    assert Path("reports/canary/latest_incident_drill.json").exists()
    assert Path("reports/canary/latest_rollback_plan.json").exists()
