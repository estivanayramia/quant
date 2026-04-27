from __future__ import annotations

import json
from pathlib import Path


class LocalReportWriter:
    def __init__(self, root: str | Path = "reports") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def write_markdown(self, name: str, content: str) -> Path:
        path = self.root / name
        path.write_text(content, encoding="utf-8")
        return path

    def write_json(self, name: str, content: dict[str, object]) -> Path:
        path = self.root / name
        path.write_text(
            json.dumps(content, indent=2, sort_keys=True, default=str), encoding="utf-8"
        )
        return path
