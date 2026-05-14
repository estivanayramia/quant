from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.research.replay_candidates.pm_crypto_updown_window_acquisition import (
    build_pm_crypto_updown_window_acquisition_plan,
)

REPORT_ROOT = Path("reports/sequence41/window_acquisition")


def write_pm_crypto_updown_window_acquisition_plan(
    *,
    fixture_root: str | Path,
    real_cached_artifact_roots: list[str | Path] | None = None,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    payload = build_pm_crypto_updown_window_acquisition_plan(
        fixture_root=fixture_root,
        real_cached_artifact_roots=real_cached_artifact_roots,
    )
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_window_acquisition_plan.json"
    md_path = root / "latest_window_acquisition_plan.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 41 Window Acquisition Plan",
        "",
        "Real-cached UP/DOWN replay window acquisition plan. Live and canary remain blocked.",
        "",
        f"Status: {payload['capture_or_import_status']}",
        f"Current primary rows: {payload['current_primary_row_count']}",
        f"Current real-cached rows: {payload['current_real_cached_row_count']}",
        f"Target primary rows: {payload['target_primary_row_count']}",
        f"Row gap: {payload['row_gap']}",
        f"Additional two-token windows needed: {payload['required_remaining_two_token_windows']}",
        f"Operator action required: {payload['operator_action_required']}",
        f"Code missing: {payload['code_missing']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        "",
        "## Required Artifacts Per Window",
    ]
    lines.extend(f"- {item}" for item in payload["required_artifacts_per_window"])
    lines.extend(["", "## Operator Commands"])
    lines.extend(f"- `{item}`" for item in payload["operator_commands"])
    lines.extend(["", "## Blockers"])
    lines.extend(f"- {item}" for item in (payload["blockers"] or ["None"]))
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
