from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class StrategyEvidence:
    strategy_id: str
    metrics: dict[str, Any]
    validation_reports: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    live_promotion_status: str = "TINY_LIVE_BLOCKED"

    @property
    def live_ready(self) -> bool:
        return False
