from __future__ import annotations

from pydantic import BaseModel


class StrategyRecord(BaseModel):
    strategy_id: str
    name: str
    enabled: bool = True
    quarantined: bool = False
    notes: str = ""
