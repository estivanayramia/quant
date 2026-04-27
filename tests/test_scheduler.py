from __future__ import annotations

from quant_os.autonomy.scheduler import LocalScheduler


def test_scheduler_runs_single_cycle(local_project):
    result = LocalScheduler().run(interval_minutes=1, max_cycles=1)
    assert result.cycles == 1
    assert result.stopped is True
