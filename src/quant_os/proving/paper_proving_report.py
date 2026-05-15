from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.proving.paper_proving_harness import (
    build_fixture_safe_paper_proving_input,
    run_paper_proving_harness,
)
from quant_os.proving.paper_proving_models import PaperProvingInput

REPORT_ROOT = Path("reports/paper_profit_discovery/paper_proving")


def write_paper_proving_report(
    *,
    output_root: str | Path = ".",
    proving_input: PaperProvingInput | None = None,
) -> dict[str, Any]:
    payload = run_paper_proving_harness(
        proving_input
        or build_fixture_safe_paper_proving_input(lane_id="pm_weather_forecast_market_mismatch")
    )
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_paper_proving.json"
    md_path = root / "latest_paper_proving.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Paper-Proving Diagnostic",
        "",
        "Fixture-safe paper diagnostic. Backtests are not proof and fills are simulated.",
        "",
        f"Lane: {payload['lane_id']}",
        f"Readiness status: {payload['readiness_status']}",
        f"Net simulated PnL after costs: {payload['net_simulated_pnl_after_costs']}",
        f"Fill-adjusted PnL: {payload['fill_adjusted_pnl']}",
        f"Trade count: {payload['trade_count']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Warnings",
    ]
    lines.extend(f"- {warning}" for warning in payload["warnings"])
    lines.extend(["", "## Baselines"])
    lines.extend(
        f"- {row['name']}: {row['net_pnl']}" for row in payload["baseline_comparison"]["rows"]
    )
    lines.extend(["", "## Placebos"])
    lines.extend(
        f"- {row['name']}: {row['net_pnl']}" for row in payload["placebo_comparison"]["rows"]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
