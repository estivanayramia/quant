from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class ExchangeCapabilities:
    exchange_name: str
    adapter_available: bool
    spot_only: bool = True
    supports_market_orders: bool = True
    supports_stoploss_on_exchange: bool | None = None
    supports_margin: bool = False
    supports_futures: bool = False
    supports_leverage: bool = False
    supports_shorting: bool = False
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExchangeOrderRequest:
    symbol: str
    side: str
    notional_usd: float
    client_order_id: str
    order_type: str = "market"


@dataclass(frozen=True)
class ExchangeOrderResult:
    status: str
    client_order_id: str
    exchange_order_id: str | None = None
    filled_notional_usd: float = 0.0
    message: str = ""
    raw_payload: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ExchangePosition:
    symbol: str
    side: str
    notional_usd: float
    quantity: float | None = None


class LiveCanaryExchangePort(Protocol):
    is_fake: bool

    def capabilities(self) -> ExchangeCapabilities:
        ...

    def get_open_positions(self) -> list[ExchangePosition]:
        ...

    def place_order(self, request: ExchangeOrderRequest) -> ExchangeOrderResult:
        ...

    def emergency_stop(self) -> dict[str, object]:
        ...

