from __future__ import annotations

from typing import Any


def summarize_freqtrade_logs(log_payload: dict[str, Any]) -> dict[str, Any]:
    entries = log_payload.get("entries", [])
    return {
        "line_count": log_payload.get("line_count", len(entries)),
        "warnings": log_payload.get("warnings", 0),
        "errors": log_payload.get("errors", 0),
        "pairs": log_payload.get("pairs", []),
        "dry_run_indicators": log_payload.get("dry_run_indicators", 0),
        "trade_level_metrics_available": False,
    }
