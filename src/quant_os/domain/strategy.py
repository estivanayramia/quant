from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class StrategyStatus(StrEnum):
    DRAFT = "draft"
    RESEARCH = "research"
    SHADOW = "shadow"
    PAPER = "paper"
    CANARY_CANDIDATE = "canary_candidate"
    QUARANTINED = "quarantined"
    RETIRED = "retired"


class StrategyRecord(BaseModel):
    strategy_id: str
    name: str
    enabled: bool = True
    quarantined: bool = False
    status: StrategyStatus = StrategyStatus.RESEARCH
    notes: str = ""
