from __future__ import annotations

from quant_os.data.providers.base import ProviderAvailability


class LocalFileProvider:
    name = "LOCAL_FILE"

    def availability(self) -> ProviderAvailability:
        return ProviderAvailability(
            name=self.name,
            enabled=True,
            available=True,
            requires_network=False,
            requires_keys=False,
            reason="local file imports are available",
        )
