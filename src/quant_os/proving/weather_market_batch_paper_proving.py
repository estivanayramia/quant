from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.proving.weather_market_real_paper_proving import (
    run_weather_market_real_paper_proving,
)
from quant_os.research.replay_candidates.weather_market_replay_schema import (
    WeatherMarketReplayRow,
)

REPORT_ROOT = Path("reports/sequence52/weather_batch_paper_proving")


def run_weather_market_batch_paper_proving(
    rows: list[dict[str, Any] | WeatherMarketReplayRow],
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    payload = run_weather_market_real_paper_proving(rows, output_root=output_root)
    payload.update(
        {
            "schema_version": "weather_market_batch_paper_proving_v1",
            "sequence": "52",
        }
    )
    if payload.get("proof_row_count", 0) >= 30 and not payload.get("blockers"):
        payload["oos_walk_forward_status"] = "OOS_WALK_FORWARD_AVAILABLE"
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def write_weather_market_batch_paper_proving_report(
    *,
    output_root: str | Path = ".",
    rows: list[dict[str, Any] | WeatherMarketReplayRow] | None = None,
) -> dict[str, Any]:
    if rows is None:
        from quant_os.research.replay_candidates.weather_market_resolved_dataset_builder import (
            write_weather_market_resolved_dataset_report,
        )

        dataset = write_weather_market_resolved_dataset_report(output_root=output_root)
        rows = dataset.get("rows", [])
    return run_weather_market_batch_paper_proving(rows, output_root=output_root)


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_weather_batch_paper_proving.json"
    md_path = root / "latest_weather_batch_paper_proving.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 52 Weather Batch Paper Proving",
        "",
        "Honest paper proving over proof-eligible public weather rows.",
        "",
        f"Status: {payload['readiness_status']}",
        f"Proof rows: {payload['proof_row_count']}",
        f"Net simulated PnL after costs: {payload['net_simulated_pnl_after_costs']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Warnings",
    ]
    lines.extend(f"- {item}" for item in payload.get("warnings", []) or ["None"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
