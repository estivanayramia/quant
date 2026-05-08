from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any


def normalize_decimal(value: Any) -> str | None:
    if value is None:
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return str(value)
    rendered = format(parsed, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered or "0"


@dataclass(frozen=True)
class PredictionMarketReplayEvent:
    event_type: str
    source_id: str
    provenance: str
    timestamp: str | None = None
    market_id: str | None = None
    condition_id: str | None = None
    slug: str | None = None
    token_id: str | None = None
    outcome: str | None = None
    best_bid_price: str | None = None
    best_bid_size: str | None = None
    best_ask_price: str | None = None
    best_ask_size: str | None = None
    trade_price: str | None = None
    trade_size: str | None = None
    snapshot_id: str | None = None
    quality_flags: tuple[str, ...] = ()
    raw_metadata: dict[str, Any] = field(default_factory=dict, compare=False, repr=False)

    def to_report_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "source_id": self.source_id,
            "provenance": self.provenance,
            "timestamp": self.timestamp,
            "market_id": self.market_id,
            "condition_id": self.condition_id,
            "slug": self.slug,
            "token_id": self.token_id,
            "outcome": self.outcome,
            "best_bid_price": self.best_bid_price,
            "best_bid_size": self.best_bid_size,
            "best_ask_price": self.best_ask_price,
            "best_ask_size": self.best_ask_size,
            "trade_price": self.trade_price,
            "trade_size": self.trade_size,
            "snapshot_id": self.snapshot_id,
            "quality_flags": list(self.quality_flags),
        }
