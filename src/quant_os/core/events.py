from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from quant_os.core.ids import new_event_id
from quant_os.core.time import utc_now


class EventType(StrEnum):
    DATA_SEEDED = "DATA_SEEDED"
    BACKTEST_STARTED = "BACKTEST_STARTED"
    BACKTEST_COMPLETED = "BACKTEST_COMPLETED"
    ORDER_SUBMITTED = "ORDER_SUBMITTED"
    ORDER_ACCEPTED = "ORDER_ACCEPTED"
    ORDER_REJECTED = "ORDER_REJECTED"
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    POSITION_OPENED = "POSITION_OPENED"
    POSITION_UPDATED = "POSITION_UPDATED"
    POSITION_CLOSED = "POSITION_CLOSED"
    RISK_APPROVED = "RISK_APPROVED"
    RISK_REJECTED = "RISK_REJECTED"
    KILL_SWITCH_ACTIVATED = "KILL_SWITCH_ACTIVATED"
    KILL_SWITCH_DEACTIVATED = "KILL_SWITCH_DEACTIVATED"
    STRATEGY_QUARANTINED = "STRATEGY_QUARANTINED"
    STRATEGY_RELEASED = "STRATEGY_RELEASED"
    REPORT_GENERATED = "REPORT_GENERATED"


class DomainEvent(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    event_id: str = Field(default_factory=new_event_id)
    event_type: EventType
    timestamp: datetime = Field(default_factory=utc_now)
    aggregate_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    schema_version: int = 1


def make_event(
    event_type: EventType,
    aggregate_id: str,
    payload: dict[str, Any] | None = None,
) -> DomainEvent:
    return DomainEvent(
        event_type=event_type,
        aggregate_id=aggregate_id,
        payload=payload or {},
    )
