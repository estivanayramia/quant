from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ProviderAvailability:
    name: str
    enabled: bool
    available: bool
    requires_network: bool
    requires_keys: bool
    reason: str


class HistoricalDataProvider(Protocol):
    name: str

    def availability(self) -> ProviderAvailability:
        """Return provider availability without fetching data."""
