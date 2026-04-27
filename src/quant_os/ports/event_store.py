from __future__ import annotations

from typing import Protocol

from quant_os.core.events import DomainEvent


class EventStorePort(Protocol):
    def append(self, event: DomainEvent) -> None: ...

    def read_all(self) -> list[DomainEvent]: ...
