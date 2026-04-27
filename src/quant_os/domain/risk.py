from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from quant_os.core.time import utc_now


class RiskDecision(BaseModel):
    approved: bool
    reasons: list[str] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=utc_now)
    limits_snapshot: dict[str, object] = Field(default_factory=dict)
    strategy_id: str | None = None
    symbol: str | None = None
    client_order_id: str | None = None
