from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_window_labels(path: str | Path) -> dict[str, dict[str, Any]]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    labels = {}
    for item in raw:
        labels[str(item["market_id"])] = {
            "market_id": str(item["market_id"]),
            "resolved_outcome": (
                None if item.get("resolved_outcome") is None else str(item["resolved_outcome"])
            ),
            "label_status": str(item["label_status"]),
            "resolution_source_id": str(item.get("resolution_source_id", "unknown_label_source")),
        }
    return dict(sorted(labels.items()))
