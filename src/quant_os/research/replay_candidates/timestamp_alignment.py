from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from quant_os.data.crypto_spot_snapshots import parse_utc


def asof_snapshot(
    rows: list[dict[str, Any]],
    *,
    timestamp: datetime,
    timestamp_field: str,
    symbol: str | None = None,
) -> dict[str, Any] | None:
    candidates = []
    for row in rows:
        if symbol is not None and row.get("symbol") != symbol:
            continue
        row_ts = parse_utc(str(row[timestamp_field]))
        if row_ts <= timestamp:
            candidates.append((row_ts, row))
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item[0])[-1][1]


def seconds_between(left: str, right: str) -> float:
    return (parse_utc(right) - parse_utc(left)).total_seconds()


def shifted_timestamp(timestamp: datetime, *, seconds: int) -> datetime:
    return timestamp - timedelta(seconds=seconds)
