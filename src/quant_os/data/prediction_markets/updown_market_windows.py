from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.data.crypto_spot_snapshots import parse_utc, utc_string


def load_updown_market_windows(path: str | Path) -> list[dict[str, Any]]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    windows = []
    for item in raw:
        windows.append(
            {
                "market_id": str(item["market_id"]),
                "condition_id": str(item["condition_id"]),
                "slug": str(item["slug"]),
                "spot_symbol": str(item["spot_symbol"]),
                "window_start_ts": utc_string(parse_utc(str(item["window_start_ts"]))),
                "window_end_ts": utc_string(parse_utc(str(item["window_end_ts"]))),
                "tokens": [
                    {"token_id": str(token["token_id"]), "outcome": str(token["outcome"])}
                    for token in item["tokens"]
                ],
            }
        )
    return sorted(windows, key=lambda item: item["market_id"])
