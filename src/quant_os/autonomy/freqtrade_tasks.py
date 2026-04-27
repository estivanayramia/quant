from __future__ import annotations

from quant_os.integrations.freqtrade.dry_run_adapter import FreqtradeDryRunAdapter
from quant_os.ops.freqtrade_reporting import write_freqtrade_status_report


def freqtrade_safe_lane_status() -> dict[str, object]:
    adapter = FreqtradeDryRunAdapter()
    if not adapter.dry_run_available():
        adapter.generate_config()
        adapter.export_strategy()
    adapter.validate_config()
    adapter.write_run_manifest()
    status = write_freqtrade_status_report()
    return {
        "freqtrade": {
            "enabled": False,
            "dry_run_config_present": status["dry_run_config_present"],
            "safety_guard_passed": status["safety_guard_passed"],
            "strategy_exported": status["strategy_exported"],
            "docker_available": status["docker_available"],
            "next_manual_command": status["next_manual_command"],
        }
    }
