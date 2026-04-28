from __future__ import annotations

from typing import Any

from quant_os.monitoring.monitoring_report import generate_dryrun_monitoring_report


def write_dryrun_monitoring_report() -> dict[str, Any]:
    return generate_dryrun_monitoring_report()
