from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from quant_os.autonomy.dry_run_proving import DryRunProvingConfig, run_dry_run_proving_cycle


@dataclass(frozen=True)
class ProvingSchedule:
    cycles: int = 1


def run_proving_schedule(
    *,
    schedule: ProvingSchedule | None = None,
    config: DryRunProvingConfig | None = None,
) -> dict[str, Any]:
    active_schedule = schedule or ProvingSchedule()
    results = [run_dry_run_proving_cycle(config=config) for _ in range(active_schedule.cycles)]
    latest = results[-1] if results else {}
    return {
        "cycle_count": len(results),
        "latest_status": latest.get("status", "NOT_READY"),
        "results": results,
        "live_trading_enabled": False,
        "live_promotion_status": "LIVE_BLOCKED",
    }
