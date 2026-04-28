from __future__ import annotations

from typing import Any

from quant_os.monitoring.dryrun_history import load_history_records


def project_dryrun_history(window_days: int | None = None) -> dict[str, Any]:
    records = load_history_records(window_days)
    return {
        "records_count": len(records),
        "latest": records[-1] if records else None,
        "records": records,
    }
