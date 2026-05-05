from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def load_prediction_market_history(path: str | Path) -> dict[str, Any]:
    history_path = Path(path)
    payload = json.loads(history_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = "prediction-market history fixture must contain a JSON object"
        raise ValueError(msg)
    markets = payload.get("markets")
    if not isinstance(markets, list):
        msg = "prediction-market history fixture must expose a markets list"
        raise ValueError(msg)
    return payload


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
