from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class ValidationScenario(BaseModel):
    scenario_id: str
    description: str
    expected_action: str
    validator: str


class ValidationOutcome(BaseModel):
    scenario_id: str
    status: str
    action: str
    blocked_correctly: bool = False
    unsafe_action_count: int = 0
    reason_codes: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    live_trading_enabled: bool = False
