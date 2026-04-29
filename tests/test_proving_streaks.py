from __future__ import annotations

from quant_os.proving.streaks import compute_streaks


def test_success_failure_streaks_compute_correctly() -> None:
    records = [
        {"run_status": "completed", "proving_blockers": []},
        {"run_status": "completed", "proving_blockers": []},
        {"run_status": "failed", "proving_blockers": ["RUNBOOK_FAILURE"]},
        {"run_status": "completed", "proving_blockers": []},
    ]
    streaks = compute_streaks(records)
    assert streaks["current_success_streak"] == 1
    assert streaks["longest_success_streak"] == 2
    assert streaks["failed_runs"] == 1
