from __future__ import annotations

from typing import Any

from quant_os.proving.streaks import compute_streaks


def proving_metric_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    streaks = compute_streaks(records)
    return {
        "total_runs": streaks["total_runs"],
        "successful_runs": streaks["successful_runs"],
        "failed_runs": streaks["failed_runs"],
        "warning_runs": streaks["warning_runs"],
        "current_success_streak": streaks["current_success_streak"],
    }
