from __future__ import annotations

from dataclasses import dataclass

from quant_os.live_canary.exchange_port import (
    ExchangeCapabilities,
    ExchangeOrderRequest,
    ExchangeOrderResult,
    ExchangePosition,
)


@dataclass
class CanaryExchangeAdapter:
    """Unavailable-by-default live adapter placeholder."""

    exchange_name: str = "canary_exchange"
    is_fake: bool = False

    def capabilities(self) -> ExchangeCapabilities:
        return ExchangeCapabilities(
            exchange_name=self.exchange_name,
            adapter_available=False,
            supports_stoploss_on_exchange=None,
            notes=["real exchange transport is not configured in the base install"],
        )

    def get_open_positions(self) -> list[ExchangePosition]:
        return []

    def place_order(self, request: ExchangeOrderRequest) -> ExchangeOrderResult:
        return ExchangeOrderResult(
            status="REJECTED",
            client_order_id=request.client_order_id,
            message="real exchange transport unavailable in base install",
        )

    def emergency_stop(self) -> dict[str, object]:
        return {
            "status": "UNAVAILABLE",
            "exchange_name": self.exchange_name,
            "fake": False,
            "reason": "real exchange transport unavailable in base install",
        }

