from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def load_crypto_spot_snapshots(path: str | Path) -> list[dict[str, Any]]:
    rows = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows.append(
                {
                    "timestamp_utc": _utc_string(row["timestamp_utc"]),
                    "symbol": row["symbol"],
                    "price": float(row["price"]),
                    "source_id": row.get("source_id", "unknown_spot_source"),
                }
            )
    return sorted(rows, key=lambda item: (item["symbol"], item["timestamp_utc"]))


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(UTC)


def utc_string(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _utc_string(value: str) -> str:
    return utc_string(parse_utc(value))
