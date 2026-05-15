from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.proving.profit_claim_guard import evaluate_profit_claim_guard
from quant_os.proving.weather_market_paper_proving import run_weather_market_paper_proving
from quant_os.research.replay_candidates.weather_market_replay_schema import (
    load_weather_market_replay_rows,
)

REPORT_ROOT = Path("reports/sequence50/weather_paper_proving")
DEFAULT_FIXTURE_PATH = (
    Path("tests")
    / "fixtures"
    / "replay_candidates"
    / "weather_market_mismatch"
    / "fixture_only_rows.json"
)


def write_weather_market_paper_proving_report(
    *,
    output_root: str | Path = ".",
    fixture_path: str | Path = DEFAULT_FIXTURE_PATH,
) -> dict[str, Any]:
    rows = load_weather_market_replay_rows(fixture_path)
    payload = run_weather_market_paper_proving(rows)
    payload["profit_claim_guard"] = evaluate_profit_claim_guard(payload)
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_weather_paper_proving.json"
    md_path = root / "latest_weather_paper_proving.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 50 Weather Market Paper Proving",
        "",
        "Fixture-safe diagnostic paper proving. No profit, live, or canary claim.",
        "",
        f"Status: {payload['readiness_status']}",
        f"Dataset status: {payload['dataset_status']}",
        f"Profit guard: {payload['profit_claim_guard']['claim_status']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Guard Blockers",
    ]
    lines.extend(f"- {item}" for item in payload["profit_claim_guard"]["blockers"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}

