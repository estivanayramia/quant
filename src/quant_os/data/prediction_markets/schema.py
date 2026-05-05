from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class MarketLifecycleStatus(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    RESOLVED = "RESOLVED"
    DISPUTED = "DISPUTED"
    AMBIGUOUS = "AMBIGUOUS"


class PredictionMarketOutcome(BaseModel):
    outcome_id: str
    name: str
    contract_name: str
    probability: float | None = None
    price: float | None = None
    winning: bool | None = None
    source_outcome_id: str | None = None


class PredictionMarketRecord(BaseModel):
    schema_version: str = "1.0"
    source: str = "polymarket"
    source_mode: str = "fixture"
    market_id: str
    condition_id: str | None = None
    slug: str | None = None
    title: str | None = None
    question: str | None = None
    description: str | None = None
    status: MarketLifecycleStatus = MarketLifecycleStatus.AMBIGUOUS
    outcomes: list[PredictionMarketOutcome] = Field(default_factory=list)
    end_time: datetime | None = None
    resolution_time: datetime | None = None
    volume: float | None = None
    liquidity: float | None = None
    open_interest: float | None = None
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    event_id: str | None = None
    captured_at: datetime | None = None
    updated_at: datetime | None = None
    source_url: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)
    raw: dict[str, Any] = Field(default_factory=dict)

    @property
    def join_keys(self) -> dict[str, str | None]:
        return {
            "source": self.source,
            "market_id": self.market_id,
            "condition_id": self.condition_id,
        }

    @property
    def binary_contract_names(self) -> list[str]:
        return [outcome.contract_name for outcome in self.outcomes]
