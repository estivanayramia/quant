from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MockAlert:
    messages: list[tuple[str, str]] = field(default_factory=list)

    def send(self, level: str, message: str) -> None:
        self.messages.append((level, message))
