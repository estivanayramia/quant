from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.readiness.pm_lp_refresh_lag_source_readiness import (
    evaluate_pm_lp_refresh_lag_source_readiness,
    load_pm_lp_refresh_lag_public_source_sample,
)

REPORT_ROOT = Path("reports/sequence48/source_readiness")


def write_pm_lp_refresh_lag_source_readiness_report(
    *,
    fixture_path: str | Path | None = None,
    output_root: str | Path = ".",
    field_status_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    fixture_payload = (
        load_pm_lp_refresh_lag_public_source_sample(fixture_path)
        if fixture_path is not None
        else None
    )
    payload = evaluate_pm_lp_refresh_lag_source_readiness(
        field_status_overrides=field_status_overrides,
        fixture_payload=fixture_payload,
    )
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_source_readiness.json"
    md_path = root / "latest_source_readiness.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 48 PM LP Refresh-Lag Source Readiness",
        "",
        "Replay-input source readiness gate. Live and canary readiness remain blocked.",
        "",
        f"Status: {payload['source_readiness_status']}",
        f"Active blocker: {payload['active_blocker']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Missing Source Fields",
    ]
    lines.extend(f"- {field}" for field in payload["exact_missing_source_fields"] or ["None"])
    lines.extend(["", "## Baseline Placebo Fill Requirements"])
    lines.extend(f"- {item}" for item in payload["baseline_placebo_fill_requirements"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
