from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from quant_os.core.time import utc_now


class KillSwitchState(BaseModel):
    active: bool = False
    reason: str | None = None
    updated_at: datetime = Field(default_factory=utc_now)

    def activate(self, reason: str = "manual") -> None:
        self.active = True
        self.reason = reason
        self.updated_at = utc_now()

    def deactivate(self) -> None:
        self.active = False
        self.reason = None
        self.updated_at = utc_now()
