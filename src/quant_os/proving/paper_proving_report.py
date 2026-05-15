from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.proving.paper_proving_harness import (
    build_default_paper_proving_input,
    run_paper_proving,
)

REPORT_ROOT = Path("reports/sequence49/paper_proving")


def write_paper_proving_report(
    *,
    output_root: str | Path = ".",
    paper_input: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = run_paper_proving(paper_input or build_default_paper_proving_input())
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_paper_proving_report.json"
    md_path = root / "latest_paper_proving_report.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 49 Paper Proving Report",
        "",
        "Deterministic paper/replay diagnostics only. No live orders or profitability claim.",
        "",
        f"Status: {payload['readiness_status']}",
        f"Lane: {payload['lane_id']}",
        f"Net simulated PnL after costs: {payload['net_simulated_pnl_after_costs']}",
        f"Trade count: {payload['trade_count']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Warnings",
    ]
    lines.extend(f"- {item}" for item in payload["warnings"])
    lines.extend(["", "## Comparisons"])
    lines.append(f"- Baseline included: {payload['baseline_comparison']['included']}")
    lines.append(f"- Placebo included: {payload['placebo_comparison']['included']}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
