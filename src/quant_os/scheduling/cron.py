from __future__ import annotations


def cron_entry(interval_minutes: int = 60) -> str:
    if interval_minutes >= 60:
        return "0 * * * * cd /path/to/quant && python -m quant_os.cli autonomous run-once"
    return f"*/{interval_minutes} * * * * cd /path/to/quant && python -m quant_os.cli autonomous run-once"
