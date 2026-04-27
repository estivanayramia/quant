from __future__ import annotations

from pathlib import Path
from typing import Protocol

from quant_os.core.events import DomainEvent


class ReadModelStorePort(Protocol):
    def rebuild(self, events: list[DomainEvent]) -> Path: ...
