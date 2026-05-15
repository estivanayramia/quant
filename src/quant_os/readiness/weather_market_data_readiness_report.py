from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.readiness.autonomy_milestone_report import (
    write_sequence50_autonomy_milestone_report,
)
from quant_os.readiness.weather_market_data_readiness import (
    evaluate_weather_market_data_readiness,
)

REPORT_ROOT = Path("reports/sequence50/weather_data_readiness")


def write_weather_market_data_readiness_report(
    *,
    output_root: str | Path = ".",
    fixture_path: str | Path | None = None,
) -> dict[str, Any]:
    kwargs = {"fixture_path": fixture_path} if fixture_path else {}
    payload = evaluate_weather_market_data_readiness(**kwargs)
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    payload["autonomy_milestone_report"] = write_sequence50_autonomy_milestone_report(
        weather_readiness=payload,
        output_root=output_root,
    )
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_weather_data_readiness.json"
    md_path = root / "latest_weather_data_readiness.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 50 Weather Data Readiness",
        "",
        "Readiness gate for weather paper proving. Live and canary remain blocked.",
        "",
        f"Status: {payload['readiness_status']}",
        f"Paper profit status: {payload['paper_profit_status']}",
        f"Dataset status: {payload['dataset_status']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Blockers",
    ]
    lines.extend(f"- {item}" for item in payload["blockers"])
    lines.extend(["", "## Exact Next Commands"])
    lines.extend(f"- `{item}`" for item in payload["exact_next_commands"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}

