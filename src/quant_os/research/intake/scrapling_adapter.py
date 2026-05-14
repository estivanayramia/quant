from __future__ import annotations

import html.parser
import importlib.util
from pathlib import Path


class _TextExtractor(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        value = " ".join(data.split())
        if value:
            self.parts.append(value)

    def text(self) -> str:
        return " ".join(self.parts)


def is_scrapling_available(*, force_absent: bool = False) -> bool:
    if force_absent:
        return False
    return importlib.util.find_spec("scrapling") is not None


def parse_cached_text_or_html(path: str | Path) -> dict[str, str]:
    artifact_path = Path(path)
    raw = artifact_path.read_text(encoding="utf-8")
    if artifact_path.suffix.lower() in {".html", ".htm"}:
        parser = _TextExtractor()
        parser.feed(raw)
        text = parser.text()
        parser_name = "cached_html_builtin_parser"
    else:
        text = raw
        parser_name = "cached_text_builtin_parser"
    return {
        "text": text,
        "raw": raw,
        "parser": parser_name,
    }
