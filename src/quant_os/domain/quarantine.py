from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from quant_os.core.time import utc_now


class StrategyQuarantineState(BaseModel):
    quarantined: dict[str, str] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=utc_now)

    def quarantine(self, strategy_id: str, reason: str) -> None:
        self.quarantined[strategy_id] = reason
        self.updated_at = utc_now()

    def release(self, strategy_id: str) -> None:
        self.quarantined.pop(strategy_id, None)
        self.updated_at = utc_now()

    def is_quarantined(self, strategy_id: str) -> bool:
        return strategy_id in self.quarantined
