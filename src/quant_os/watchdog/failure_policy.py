from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FailurePolicy:
    max_consecutive_failures: int = 3
    stop_on_failure: bool = True

    def should_stop(self, consecutive_failures: int) -> bool:
        return self.stop_on_failure and consecutive_failures >= self.max_consecutive_failures
