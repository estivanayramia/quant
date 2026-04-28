from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from quant_os.features.feature_store_local import build_feature_frame
from quant_os.research.backtest import run_backtest
from quant_os.research.research_report import ensure_research_data


def classify_regimes(frame: pd.DataFrame) -> pd.DataFrame:
    data = build_feature_frame(frame)
    pieces = []
    for _, group in data.groupby("symbol", sort=False):
        group = group.copy()
        trend = group["close"].pct_change(20).fillna(0.0)
        vol = group["returns"].rolling(20, min_periods=2).std().fillna(0.0)
        vol_median = float(vol.median()) if len(vol) else 0.0
        group["regime"] = "choppy"
        group.loc[trend > 0.015, "regime"] = "trending_up"
        group.loc[trend < -0.015, "regime"] = "trending_down"
        group.loc[vol > vol_median * 1.25, "regime"] = "high_volatility"
        group.loc[vol < vol_median * 0.75, "regime"] = "low_volatility"
        pieces.append(group)
    return pd.concat(pieces).sort_values(["symbol", "timestamp"]).reset_index(drop=True)


def run_regime_tests(symbol: str = "SPY", strategy: str = "baseline_momentum") -> dict[str, Any]:
    frame = ensure_research_data(symbol)
    data = classify_regimes(frame)
    results: dict[str, Any] = {}
    warnings: list[str] = []
    for regime, group in data.groupby("regime"):
        if len(group) < 20:
            warnings.append(f"INSUFFICIENT_DATA_{regime}")
            continue
        result = run_backtest(group, strategy=strategy, strategy_id=f"{strategy}_{regime}")
        results[str(regime)] = {
            "rows": len(group),
            "metrics": result.metrics,
            "fills": len(result.fills),
        }
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "WARN" if warnings else "PASS",
        "symbol": symbol,
        "strategy": strategy,
        "results": results,
        "warnings": warnings,
        "live_promotion_status": "TINY_LIVE_BLOCKED",
    }
    _write_regime(payload)
    return payload


def _write_regime(payload: dict[str, Any]) -> None:
    root = Path("reports/strategy/regime")
    root.mkdir(parents=True, exist_ok=True)
    (root / "latest_regime_tests.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8"
    )
    lines = [
        "# Strategy Regime Tests",
        "",
        "Research only. No live trading.",
        "",
        f"Status: {payload['status']}",
        "",
        "## Regimes",
    ]
    for regime, result in payload["results"].items():
        lines.append(
            f"- {regime}: rows={result['rows']} trades={result['metrics'].get('number_of_trades', 0)}"
        )
    if payload["warnings"]:
        lines.extend(["", "## Warnings", *[f"- {warning}" for warning in payload["warnings"]]])
    (root / "latest_regime_tests.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
