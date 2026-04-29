from __future__ import annotations

from quant_os.proving.run_history import append_proving_record, load_proving_history
from quant_os.proving.run_record import ProvingRunRecord


def _record(run_id: str = "run_1", status: str = "completed") -> ProvingRunRecord:
    return ProvingRunRecord(
        run_id=run_id,
        timestamp=f"2024-01-01T00:00:0{run_id[-1]}+00:00",
        run_status=status,
        autonomous_status=status,
        top_strategy_id="baseline",
    )


def test_proving_run_record_can_be_created(local_project) -> None:
    status = append_proving_record(_record())
    history = load_proving_history()
    assert status["history_records_count"] == 1
    assert history[0]["run_id"] == "run_1"


def test_history_aggregates_correctly(local_project) -> None:
    append_proving_record(_record("run_1"))
    append_proving_record(_record("run_2", status="failed"))
    status = append_proving_record(_record("run_3"))
    assert status["streaks"]["total_runs"] == 3
    assert status["streaks"]["successful_runs"] == 2
    assert status["streaks"]["failed_runs"] == 1
