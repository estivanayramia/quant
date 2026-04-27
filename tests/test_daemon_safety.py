from __future__ import annotations

from pathlib import Path

from quant_os.autonomy.daemon import daemon_status, run_daemon, stop_daemon


def test_daemon_runs_single_cycle_and_releases_lock(local_project):
    result = run_daemon(interval_minutes=1, max_cycles=1)
    assert result.cycles == 1
    assert daemon_status()["running"] is False


def test_daemon_stop_writes_stop_file(local_project):
    status = stop_daemon()
    assert status["stop_requested"] is True
    assert Path("reports/autonomy/daemon.stop").exists()
