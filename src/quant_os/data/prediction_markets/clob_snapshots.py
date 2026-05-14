from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.data.crypto_spot_snapshots import parse_utc, utc_string


def load_clob_snapshots(path: str | Path) -> list[dict[str, Any]]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    snapshots = []
    for item in raw:
        snapshots.append(
            {
                "clob_snapshot_id": str(item["clob_snapshot_id"]),
                "market_id": str(item["market_id"]),
                "token_id": str(item["token_id"]),
                "event_ts": utc_string(parse_utc(str(item["event_ts"]))),
                "bid": float(item["bid"]),
                "ask": float(item["ask"]),
                "last_trade_price": float(item["last_trade_price"]),
                "volume": float(item["volume"]),
                "liquidity": float(item["liquidity"]),
                "source_id": str(item.get("source_id", "unknown_clob_source")),
            }
        )
    return sorted(
        snapshots,
        key=lambda item: (item["market_id"], item["token_id"], item["event_ts"]),
    )
