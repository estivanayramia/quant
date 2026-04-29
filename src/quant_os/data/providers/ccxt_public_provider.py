from __future__ import annotations

from quant_os.data.providers.base import ProviderAvailability


class CcxtPublicProvider:
    name = "CCXT_PUBLIC"

    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled

    def availability(self) -> ProviderAvailability:
        return ProviderAvailability(
            name=self.name,
            enabled=self.enabled,
            available=False,
            requires_network=True,
            requires_keys=False,
            reason="ccxt is an optional future public-data dependency; no network in CI",
        )
