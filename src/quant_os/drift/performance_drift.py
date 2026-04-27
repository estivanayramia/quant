from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.drift.data_drift import DriftSignal


def detect_performance_drift(
    latest_metrics: dict[str, Any] | None = None,
    max_drawdown_threshold: float = -0.10,
    win_rate_collapse_threshold: float = 0.25,
) -> DriftSignal:
    metrics = latest_metrics or _load_latest_metrics()
    max_drawdown = float(metrics.get("max_drawdown", 0.0) or 0.0)
    win_rate = float(metrics.get("win_rate", 1.0) or 0.0)
    profit_factor = float(metrics.get("profit_factor", 0.0) or 0.0)
    detected = (
        max_drawdown < max_drawdown_threshold
        or win_rate < win_rate_collapse_threshold
        or profit_factor == 0.0
    )
    return DriftSignal(
        name="performance_drift",
        detected=detected,
        severity="warning" if detected else "ok",
        details={
            "max_drawdown": max_drawdown,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
        },
    )


def _load_latest_metrics() -> dict[str, Any]:
    path = Path("reports/tournament_summary.json")
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    results = payload.get("results", {})
    return next(iter(results.values()), {}) if isinstance(results, dict) else {}
