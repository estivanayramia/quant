from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from quant_os.research.backtest import run_backtest
from quant_os.research.research_report import ensure_research_data


def walk_forward_splits(
    frame: pd.DataFrame,
    *,
    minimum_splits: int = 3,
    train_ratio: float = 0.6,
) -> list[tuple[pd.DataFrame, pd.DataFrame]]:
    data = frame.sort_values("timestamp").reset_index(drop=True)
    if len(data) < 60:
        return []
    train_size = max(20, int(len(data) * train_ratio / minimum_splits))
    test_size = max(10, int((len(data) - train_size) / minimum_splits))
    splits: list[tuple[pd.DataFrame, pd.DataFrame]] = []
    start = 0
    while start + train_size + test_size <= len(data) and len(splits) < minimum_splits:
        train = data.iloc[start : start + train_size].copy()
        test = data.iloc[start + train_size : start + train_size + test_size].copy()
        splits.append((train, test))
        start += test_size
    return splits


def run_walk_forward_validation(
    symbol: str = "SPY",
    strategy: str = "baseline_momentum",
) -> dict[str, Any]:
    frame = ensure_research_data(symbol)
    splits = walk_forward_splits(frame)
    warnings: list[str] = []
    if not splits:
        payload = {
            "generated_at": datetime.now(UTC).isoformat(),
            "status": "UNAVAILABLE",
            "reason": "INSUFFICIENT_DATA",
            "splits": [],
            "warnings": ["INSUFFICIENT_DATA"],
            "live_promotion_status": "TINY_LIVE_BLOCKED",
        }
        _write_walk_forward(payload)
        return payload
    split_results = []
    returns = []
    for index, (_train, test) in enumerate(splits, start=1):
        result = run_backtest(test, strategy=strategy, strategy_id=f"{strategy}_wf_{index}")
        total_return = float(result.metrics.get("total_return", 0.0))
        returns.append(total_return)
        split_results.append(
            {
                "split": index,
                "test_rows": len(test),
                "metrics": result.metrics,
                "fills": len(result.fills),
            }
        )
    if len(returns) > 1 and pd.Series(returns).std() > max(
        abs(pd.Series(returns).mean()) * 2, 0.02
    ):
        warnings.append("UNSTABLE_WALK_FORWARD_RESULTS")
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "WARN" if warnings else "PASS",
        "symbol": symbol,
        "strategy": strategy,
        "splits": split_results,
        "aggregate": {
            "mean_total_return": float(pd.Series(returns).mean()),
            "std_total_return": float(pd.Series(returns).std(ddof=0)),
            "split_count": len(split_results),
        },
        "warnings": warnings,
        "live_promotion_status": "TINY_LIVE_BLOCKED",
    }
    _write_walk_forward(payload)
    return payload


def _write_walk_forward(payload: dict[str, Any]) -> None:
    root = Path("reports/strategy/walk_forward")
    root.mkdir(parents=True, exist_ok=True)
    (root / "latest_walk_forward.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8"
    )
    lines = [
        "# Walk-Forward Validation",
        "",
        "Research only. No live trading.",
        "",
        f"Status: {payload['status']}",
        f"Live promotion: {payload['live_promotion_status']}",
    ]
    if payload.get("splits"):
        lines.extend(["", "## Splits"])
        for split in payload["splits"]:
            lines.append(
                f"- split {split['split']}: rows={split['test_rows']} "
                f"return={split['metrics'].get('total_return', 0.0):.6f}"
            )
    if payload.get("warnings"):
        lines.extend(["", "## Warnings", *[f"- {warning}" for warning in payload["warnings"]]])
    (root / "latest_walk_forward.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
