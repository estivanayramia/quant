from __future__ import annotations

from pathlib import Path
from typing import Any


def build_crypto_spot_manual_capture_instructions(
    *,
    capture_root: str | Path = Path("data/external/manual_captures/pm_crypto_updown"),
) -> dict[str, Any]:
    root = Path(capture_root)
    return {
        "target": "crypto_spot_snapshots_or_candles",
        "manual_only": True,
        "read_only": True,
        "network_enabled": False,
        "network_fetch_attempted": False,
        "symbols": ["BTC-USD"],
        "required_columns": ["timestamp_utc", "symbol", "price", "source_id"],
        "destination_path": str(root / "spot_snapshots.csv").replace("\\", "/"),
        "quality_checks": [
            "timestamps normalized to UTC Z strings",
            "no spot timestamp after paired CLOB event timestamp",
            "source id present for every row",
        ],
    }
