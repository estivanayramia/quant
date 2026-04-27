from __future__ import annotations

from typing import Protocol


class AlertPort(Protocol):
    def send(self, level: str, message: str) -> None: ...
