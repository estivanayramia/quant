from __future__ import annotations


def windows_task_scheduler_command(interval_minutes: int = 60) -> str:
    return (
        "schtasks /Create /SC MINUTE "
        f"/MO {interval_minutes} /TN QuantOSAutonomous "
        '/TR "python -m quant_os.cli autonomous run-once"'
    )
