from __future__ import annotations

from quant_os.data.providers.base import ProviderAvailability


class PublicOhlcvProvider:
    name = "PUBLIC_OHLCV"

    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled

    def availability(self) -> ProviderAvailability:
        return ProviderAvailability(
            name=self.name,
            enabled=self.enabled,
            available=False,
            requires_network=True,
            requires_keys=False,
            reason="network public OHLCV provider scaffold; disabled by default",
        )
