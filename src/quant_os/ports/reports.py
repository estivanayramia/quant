from __future__ import annotations

from pathlib import Path
from typing import Protocol


class ReportWriterPort(Protocol):
    def write_markdown(self, name: str, content: str) -> Path: ...

    def write_json(self, name: str, content: dict[str, object]) -> Path: ...
