from __future__ import annotations

from pathlib import Path

from quant_os.live_canary.config import load_live_execution_config
from quant_os.live_canary.exchange_fake import FakeLiveCanaryExchange
from quant_os.live_canary.exchange_port import LiveCanaryExchangePort
from quant_os.live_canary.exchange_real import KrakenSpotCanaryAdapter


def build_exchange_adapter(
    *,
    fake: bool = False,
    stoploss_supported: bool | None = True,
    settings_path: str | Path | None = None,
    credential_path: str | Path | None = None,
) -> LiveCanaryExchangePort:
    if fake:
        return FakeLiveCanaryExchange(stoploss_supported=stoploss_supported)
    config = load_live_execution_config()
    adapter_config = config.get("adapter", {})
    if adapter_config.get("type", "fake") == "fake":
        return FakeLiveCanaryExchange(stoploss_supported=stoploss_supported)
    return KrakenSpotCanaryAdapter(settings_path=settings_path, credential_path=credential_path)
