from __future__ import annotations

import importlib.util
from typing import Any

from quant_os.data.providers.base import ProviderAvailability


class PolymarketPublicProvider:
    name = "POLYMARKET_PUBLIC"

    def __init__(
        self,
        *,
        enabled: bool = False,
        base_url: str = "https://gamma-api.polymarket.com",
        timeout_seconds: float = 10.0,
    ) -> None:
        self.enabled = enabled
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def availability(self) -> ProviderAvailability:
        installed = importlib.util.find_spec("requests") is not None
        return ProviderAvailability(
            name=self.name,
            enabled=self.enabled,
            available=bool(self.enabled and installed),
            requires_network=True,
            requires_keys=False,
            reason=(
                "read-only public Polymarket metadata provider; network disabled by default"
                if installed
                else "optional requests dependency is not installed"
            ),
        )

    def capabilities(self) -> dict[str, Any]:
        return {
            "read_only": True,
            "supports_execution": False,
            "supports_authentication": False,
            "requires_private_keys": False,
            "network_default": "disabled",
            "safety_guards": [
                "READ_ONLY_PUBLIC_METADATA",
                "NO_AUTHENTICATED_ENDPOINTS",
                "NO_WALLET_SIGNING",
                "EXECUTION_NOT_SUPPORTED",
            ],
        }

    def fetch_markets(
        self,
        *,
        allow_network_fetch: bool = False,
        explicit_network_fetch: bool = False,
        limit: int = 100,
    ) -> dict[str, Any]:
        if not allow_network_fetch or not explicit_network_fetch:
            msg = "Polymarket network fetch requires allow_network_fetch and explicit_network_fetch"
            raise RuntimeError(msg)
        availability = self.availability()
        if not availability.available:
            raise RuntimeError(availability.reason)

        import requests

        response = requests.get(
            f"{self.base_url}/markets",
            params={"limit": limit},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        markets = payload if isinstance(payload, list) else payload.get("markets", [])
        return {
            "source": "polymarket_gamma_public",
            "source_mode": "network_manual",
            "markets": markets,
        }
