from __future__ import annotations

from quant_os.live_canary.config import load_live_execution_config
from quant_os.live_canary.exchange_canary import CanaryExchangeAdapter
from quant_os.live_canary.exchange_fake import FakeLiveCanaryExchange
from quant_os.live_canary.exchange_port import LiveCanaryExchangePort


def build_live_canary_adapter(
    *,
    fake: bool = False,
    stoploss_supported: bool | None = True,
) -> LiveCanaryExchangePort:
    if fake:
        return FakeLiveCanaryExchange(stoploss_supported=stoploss_supported)
    config = load_live_execution_config()
    return CanaryExchangeAdapter(exchange_name=str(config.get("exchange_name", "canary_exchange")))

