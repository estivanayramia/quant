from __future__ import annotations

from quant_os.autonomy.proving_cycle import run_proving_once
from quant_os.autonomy.supervisor import Supervisor
from quant_os.proving.incident_log import summarize_incidents
from quant_os.proving.proving_report import write_proving_report
from quant_os.proving.readiness import evaluate_proving_readiness
from quant_os.proving.run_history import build_status, load_proving_history


def test_phase10_smoke_passes(local_project) -> None:
    payload = run_proving_once()
    assert payload["readiness"]["live_promotion_status"] == "LIVE_BLOCKED"
    assert build_status()["history_records_count"] >= 1
    assert load_proving_history()
    assert summarize_incidents()["live_promotion_status"] == "LIVE_BLOCKED"
    assert evaluate_proving_readiness()["live_ready"] is False
    assert write_proving_report()["live_promotion_status"] == "LIVE_BLOCKED"
    state = Supervisor().run_once()
    assert state.proving_mode_summary["proving_mode"]["live_promotion_status"] == "LIVE_BLOCKED"
