from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from quant_os.research.crypto.candidate_strategies import (
    generate_crypto_candidate_signals,
    signals_to_rows,
    strategy_failure_modes,
)
from quant_os.research.crypto.features import build_crypto_features


def write_crypto_research_report(
    frame: pd.DataFrame,
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    output_dir = Path(output_root) / "reports" / "crypto"
    output_dir.mkdir(parents=True, exist_ok=True)
    features = build_crypto_features(frame)
    signals = generate_crypto_candidate_signals(features)
    rows = signals_to_rows(signals)
    comparisons: dict[str, dict[str, float | int]] = {
        "no_trade": {"signals": 0, "average_expected_edge_bps": 0.0}
    }
    for strategy_id in sorted({row["strategy_id"] for row in rows} | {"random_placebo"}):
        strategy_rows = [row for row in rows if row["strategy_id"] == strategy_id]
        comparisons[strategy_id] = {
            "signals": len(strategy_rows),
            "average_expected_edge_bps": float(
                sum(float(row["expected_edge_bps"]) for row in strategy_rows) / len(strategy_rows)
            )
            if strategy_rows
            else 0.0,
        }
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "RESEARCH_ONLY",
        "symbols": sorted(features["symbol"].unique().tolist()),
        "rows": int(len(features)),
        "signal_count": len(rows),
        "signals": rows,
        "baseline_comparisons": comparisons,
        "failure_modes": strategy_failure_modes(),
        "live_trading_enabled": False,
    }
    (output_dir / "latest_research.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8"
    )
    lines = [
        "# Crypto Research Report",
        "",
        "Research only. No live trading.",
        "",
        f"Status: {payload['status']}",
        f"Rows: {payload['rows']}",
        f"Signals: {payload['signal_count']}",
        "",
        "## Baselines",
    ]
    for strategy_id, comparison in comparisons.items():
        lines.append(
            f"- {strategy_id}: {comparison['signals']} signals, "
            f"{comparison['average_expected_edge_bps']:.2f} bps average expected edge"
        )
    lines.extend(["", "## Failure Modes"])
    for strategy_id, notes in payload["failure_modes"].items():
        lines.append(f"- {strategy_id}: {'; '.join(notes)}")
    (output_dir / "latest_research.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload
