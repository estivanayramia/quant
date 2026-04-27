from __future__ import annotations

from pathlib import Path

from quant_os.autonomy.supervisor import Supervisor


def test_autonomous_runbook_completes(local_project):
    state = Supervisor().run_once()
    assert state.status.value == "completed"
    assert Path("reports/autonomy/latest_run.json").exists()
    assert Path("reports/autonomy/latest_run.md").exists()
    assert any(task.name == "run_shadow_mode" for task in state.task_statuses)
    assert any(task.name == "run_drift_checks" for task in state.task_statuses)
