from __future__ import annotations

from rich import print

from quant_os.monitoring.monitoring_report import generate_dryrun_monitoring_report

if __name__ == "__main__":
    print(generate_dryrun_monitoring_report())
