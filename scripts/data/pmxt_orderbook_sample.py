"""List or download a bounded pmxt Polymarket orderbook archive sample.

Default behavior only lists candidates. Download requires --download and keeps
the selected file under ignored data/external/pmxt_orderbooks.
"""

from __future__ import annotations

import argparse
import html.parser
import json
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

import duckdb

ARCHIVE_INDEX_URL = "https://archive.pmxt.dev/Polymarket/v2/"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CACHE_DIR = REPO_ROOT / "data" / "external" / "pmxt_orderbooks"
FILE_RE = re.compile(r"polymarket_orderbook_\d{4}-\d{2}-\d{2}T\d{2}\.parquet")
SIZE_RE = re.compile(r"(?P<size>\d+(?:\.\d+)?)\s*(?P<unit>[KMGT])B")
CONTENT_RANGE_RE = re.compile(r"/(?P<bytes>\d+)$")


@dataclass(frozen=True)
class Candidate:
    name: str
    url: str
    size_mb: float | None


class LinkParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attrs_dict = dict(attrs)
        href = attrs_dict.get("href")
        if href and FILE_RE.search(href):
            self.links.append(href)


def size_to_mb(text: str) -> float | None:
    match = SIZE_RE.search(text)
    if not match:
        return None
    value = float(match.group("size"))
    unit = match.group("unit")
    return value * {"K": 1 / 1024, "M": 1, "G": 1024, "T": 1024 * 1024}[unit]


def fetch_candidates() -> list[Candidate]:
    with urllib.request.urlopen(ARCHIVE_INDEX_URL, timeout=30) as response:
        html = response.read().decode("utf-8", errors="replace")
    parser = LinkParser()
    parser.feed(html)
    candidates: list[Candidate] = []
    for link in dict.fromkeys(parser.links):
        name_match = FILE_RE.search(link)
        if not name_match:
            continue
        name = name_match.group(0)
        line = next((line for line in html.splitlines() if name in line), "")
        url = urljoin(ARCHIVE_INDEX_URL, link)
        candidates.append(Candidate(name=name, url=url, size_mb=size_to_mb(line) or fetch_head_size_mb(url)))
    return sorted(candidates, key=lambda item: (item.size_mb is None, item.size_mb or 0, item.name))


def fetch_head_size_mb(url: str) -> float | None:
    try:
        request = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(request, timeout=20) as response:
            length = response.headers.get("Content-Length")
    except Exception:
        length = None
    if not length:
        try:
            request = urllib.request.Request(
                url,
                headers={"Range": "bytes=0-0", "User-Agent": "quant-research-readonly/1.0"},
            )
            with urllib.request.urlopen(request, timeout=20) as response:
                content_range = response.headers.get("Content-Range", "")
                match = CONTENT_RANGE_RE.search(content_range)
                length = match.group("bytes") if match else None
                response.read(1)
        except Exception:
            return None
    if not length:
        return None
    return int(length) / (1024 * 1024)


def download(candidate: Candidate, cache_dir: Path, max_mb: float) -> Path:
    if candidate.size_mb is None:
        raise SystemExit(f"Refusing to download {candidate.name}: size unknown.")
    if candidate.size_mb > max_mb:
        raise SystemExit(
            f"Refusing to download {candidate.name}: {candidate.size_mb:.1f} MB exceeds "
            f"--max-mb {max_mb:.1f}."
        )
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / candidate.name
    if not target.exists():
        urllib.request.urlretrieve(candidate.url, target)
    return target


def inspect_parquet(path: Path) -> dict[str, object]:
    con = duckdb.connect()
    safe_path = path.as_posix().replace("'", "''")
    columns = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{safe_path}')").fetchall()
    rows = con.execute(f"SELECT COUNT(*) FROM read_parquet('{safe_path}')").fetchone()[0]
    return {"path": str(path), "rows": rows, "columns": columns[:20]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="download the smallest bounded sample")
    parser.add_argument("--max-mb", type=float, default=125.0)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--inspect", type=Path, help="inspect an already-downloaded parquet file")
    args = parser.parse_args()

    if args.inspect:
        print(json.dumps(inspect_parquet(args.inspect), indent=2, default=str))
        return 0

    candidates = fetch_candidates()
    print(
        json.dumps(
            {
                "archive_index": ARCHIVE_INDEX_URL,
                "downloaded": False,
                "candidates": [candidate.__dict__ for candidate in candidates[: args.limit]],
            },
            indent=2,
        )
    )

    if args.download:
        eligible = [candidate for candidate in candidates if candidate.size_mb is not None]
        if not eligible:
            raise SystemExit("No downloadable candidates with known sizes found.")
        target = download(eligible[0], args.cache_dir, args.max_mb)
        print(json.dumps({"downloaded": True, "target": str(target)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
