from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.research.intake.intake_runner import run_research_intake

REPORT_ROOT = Path("reports/sequence35/intake_run")


def write_intake_run_report(
    *,
    source_config_path: str | Path,
    output_root: str | Path = ".",
    manual_network_fetch_enabled: bool = False,
) -> dict[str, Any]:
    payload = run_research_intake(
        source_config_path=source_config_path,
        output_root=output_root,
        manual_network_fetch_enabled=manual_network_fetch_enabled,
    )
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_intake_run.json"
    md_path = root / "latest_intake_run.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 35 Governed Research Intake Run",
        "",
        "Repeatable research intake run. Local/cached artifacts only; no trading authority.",
        "",
        f"Run ID: {payload['run_id']}",
        f"Artifacts: {payload['artifact_count']}",
        f"Duplicates: {payload['duplicate_count']}",
        f"Hypotheses: {payload['hypothesis_count']}",
        f"Tasks: {payload['task_count']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Evidence Updates",
        f"- Phase 33 blocker: {payload['evidence_plan_updates']['phase33_blocker_addressed']}",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
