from __future__ import annotations

from typing import Any


def compute_streaks(records: list[dict[str, Any]]) -> dict[str, int]:
    current_success = 0
    current_failure = 0
    longest_success = 0
    longest_failure = 0
    successful = 0
    failed = 0
    for record in records:
        success = record.get("run_status") == "completed" and not record.get("proving_blockers")
        if success:
            successful += 1
            current_success += 1
            current_failure = 0
        else:
            failed += 1
            current_failure += 1
            current_success = 0
        longest_success = max(longest_success, current_success)
        longest_failure = max(longest_failure, current_failure)
    return {
        "current_success_streak": current_success,
        "current_failure_streak": current_failure,
        "longest_success_streak": longest_success,
        "longest_failure_streak": longest_failure,
        "total_runs": len(records),
        "successful_runs": successful,
        "failed_runs": failed,
        "warning_runs": sum(1 for record in records if record.get("warnings")),
    }
