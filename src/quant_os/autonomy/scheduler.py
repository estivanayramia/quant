from __future__ import annotations

import time
from dataclasses import dataclass

from quant_os.autonomy.runbook import RunbookEngine
from quant_os.autonomy.state import RunStatus


@dataclass
class SchedulerResult:
    cycles: int
    consecutive_failures: int
    stopped: bool


class LocalScheduler:
    def __init__(self, engine: RunbookEngine | None = None) -> None:
        self.engine = engine or RunbookEngine()

    def run(
        self,
        interval_minutes: int = 60,
        max_cycles: int | None = None,
        max_consecutive_failures: int = 3,
    ) -> SchedulerResult:
        cycles = 0
        failures = 0
        while True:
            result = self.engine.run()
            cycles += 1
            failures = failures + 1 if result.status == RunStatus.FAILED else 0
            if max_cycles is not None and cycles >= max_cycles:
                return SchedulerResult(cycles, failures, stopped=True)
            if failures >= max_consecutive_failures:
                return SchedulerResult(cycles, failures, stopped=True)
            time.sleep(max(1, interval_minutes * 60))
