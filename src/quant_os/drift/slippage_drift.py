from __future__ import annotations

import json
from pathlib import Path

from quant_os.drift.data_drift import DriftSignal


def detect_slippage_drift(
    summary_path: str | Path = "reports/tournament_summary.json",
) -> DriftSignal:
    path = Path(summary_path)
    if not path.exists():
        return DriftSignal(
            name="slippage_drift",
            detected=False,
            severity="ok",
            details={"summary_missing": 1},
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    results = payload.get("results", {})
    normal = _rank(results, "normal")
    stressed = _rank(results, "high_slippage")
    detected = bool(normal and stressed and normal[0] != stressed[0])
    return DriftSignal(
        name="slippage_drift",
        detected=detected,
        severity="warning" if detected else "ok",
        details={
            "normal_winner": normal[0] if normal else "",
            "high_slippage_winner": stressed[0] if stressed else "",
        },
    )


def _rank(results: dict[str, dict[str, float]], suffix: str) -> list[str]:
    filtered = {
        key: value
        for key, value in results.items()
        if key.endswith(suffix) and isinstance(value, dict)
    }
    ranked = sorted(
        filtered.items(), key=lambda item: float(item[1].get("final_equity", 0.0)), reverse=True
    )
    return [name for name, _ in ranked]
