from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ShadowOrderIntent:
    timestamp: str | None
    lane_id: str
    market_id: str | None
    token_id: str | None
    side: str
    intended_size: str
    limit_price: str | None
    price_discipline: str
    reason: str
    signal_family: str
    status: str = "CANDIDATE"
    blocking_reasons: tuple[str, ...] = ()
    execution_authority: str = "NONE"
    live_trading_enabled: bool = False
    prediction_market_execution_authority_added: bool = False
    metadata: dict[str, Any] = field(default_factory=dict, compare=False, repr=False)

    def blocked(self, reasons: list[str]) -> ShadowOrderIntent:
        return ShadowOrderIntent(
            timestamp=self.timestamp,
            lane_id=self.lane_id,
            market_id=self.market_id,
            token_id=self.token_id,
            side=self.side,
            intended_size=self.intended_size,
            limit_price=self.limit_price,
            price_discipline=self.price_discipline,
            reason=self.reason,
            signal_family=self.signal_family,
            status="BLOCKED",
            blocking_reasons=tuple(_dedupe(reasons)),
            metadata=self.metadata,
        )

    def to_report_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "lane_id": self.lane_id,
            "market_id": self.market_id,
            "token_id": self.token_id,
            "side": self.side,
            "intended_size": self.intended_size,
            "limit_price": self.limit_price,
            "price_discipline": self.price_discipline,
            "reason": self.reason,
            "signal_family": self.signal_family,
            "status": self.status,
            "blocking_reasons": list(self.blocking_reasons),
            "execution_authority": self.execution_authority,
            "live_trading_enabled": self.live_trading_enabled,
            "prediction_market_execution_authority_added": (
                self.prediction_market_execution_authority_added
            ),
        }


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    deduped = []
    for item in items:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped
