from __future__ import annotations

from quant_os.live_canary.exchange_port import ExchangeOrderRequest


def map_canary_market_order(request: ExchangeOrderRequest) -> dict[str, object]:
    return {
        "symbol": request.symbol.upper(),
        "side": request.side.lower(),
        "type": request.order_type,
        "notional_usd": request.notional_usd,
        "client_order_id": request.client_order_id,
    }

