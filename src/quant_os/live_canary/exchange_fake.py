from __future__ import annotations

from dataclasses import dataclass, field

from quant_os.live_canary.exchange_port import (
    ExchangeCapabilities,
    ExchangeOrderRequest,
    ExchangeOrderResult,
    ExchangePosition,
)


@dataclass
class FakeLiveCanaryExchange:
    exchange_name: str = "fake_canary_exchange"
    stoploss_supported: bool | None = True
    adapter_available: bool = True
    reject_orders: bool = False
    positions: list[ExchangePosition] = field(default_factory=list)

    is_fake: bool = True

    def capabilities(self) -> ExchangeCapabilities:
        return ExchangeCapabilities(
            exchange_name=self.exchange_name,
            adapter_available=self.adapter_available,
            supports_stoploss_on_exchange=self.stoploss_supported,
            notes=["fake adapter for tests and CI only"],
        )

    def get_open_positions(self) -> list[ExchangePosition]:
        return list(self.positions)

    def place_order(self, request: ExchangeOrderRequest) -> ExchangeOrderResult:
        if not self.adapter_available:
            return ExchangeOrderResult(
                status="REJECTED",
                client_order_id=request.client_order_id,
                message="fake adapter unavailable",
            )
        if self.reject_orders:
            return ExchangeOrderResult(
                status="REJECTED",
                client_order_id=request.client_order_id,
                message="fake adapter configured to reject",
            )
        if request.side.lower() == "buy":
            self.positions.append(
                ExchangePosition(
                    symbol=request.symbol,
                    side="long",
                    notional_usd=request.notional_usd,
                )
            )
        elif request.side.lower() == "sell":
            self.positions = [
                position for position in self.positions if position.symbol != request.symbol
            ]
        return ExchangeOrderResult(
            status="FIRED",
            client_order_id=request.client_order_id,
            exchange_order_id=f"fake_{request.client_order_id}",
            filled_notional_usd=request.notional_usd,
            message="fake adapter simulated order",
            raw_payload={"fake": True, "symbol": request.symbol, "side": request.side},
        )

    def emergency_stop(self) -> dict[str, object]:
        return {
            "status": "STOPPED",
            "exchange_name": self.exchange_name,
            "fake": True,
            "open_positions_count": len(self.positions),
        }

