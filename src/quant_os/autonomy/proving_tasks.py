from __future__ import annotations

from typing import Any

from quant_os.proving.incident_log import summarize_incidents
from quant_os.proving.proving_report import write_proving_report
from quant_os.proving.readiness import evaluate_proving_readiness
from quant_os.proving.run_history import build_status, load_proving_history


def proving_mode_status() -> dict[str, Any]:
    history = load_proving_history()
    status = build_status(history)
    readiness = evaluate_proving_readiness(history)
    incidents = summarize_incidents()
    write_proving_report()
    return {
        "proving_mode": {
            "enabled": True,
            "latest_status": status["status"],
            "readiness_status": readiness["readiness_status"],
            "current_success_streak": status["streaks"]["current_success_streak"],
            "current_failure_streak": status["streaks"]["current_failure_streak"],
            "unresolved_incidents": incidents["unresolved_count"],
            "blockers": readiness["blockers"],
            "latest_report_path": "reports/proving/latest_proving_report.md",
            "live_promotion_status": "LIVE_BLOCKED",
        }
    }
