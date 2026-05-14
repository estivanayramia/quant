from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.research.intake.evidence_to_shadow_bridge import (
    build_evidence_to_shadow_bridge,
)
from quant_os.research.intake.intake_run_report import write_intake_run_report

REPORT_ROOT = Path("reports/sequence35/evidence_bridge")


def write_evidence_to_shadow_report(
    *,
    source_config_path: str | Path,
    output_root: str | Path = ".",
    manual_network_fetch_enabled: bool = False,
) -> dict[str, Any]:
    intake_run = write_intake_run_report(
        source_config_path=source_config_path,
        output_root=output_root,
        manual_network_fetch_enabled=manual_network_fetch_enabled,
    )
    payload = build_evidence_to_shadow_bridge(intake_run=intake_run)
    payload["intake_run_report_paths"] = intake_run["report_paths"]
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_evidence_to_shadow_bridge.json"
    md_path = root / "latest_evidence_to_shadow_bridge.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 35 Evidence to Shadow Bridge",
        "",
        "Research tasks mapped to shadow/replay blockers. This is not execution logic.",
        "",
        f"Status: {payload['bridge_status']}",
        f"Targeted blockers: {', '.join(payload['targeted_blockers'])}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        "",
        "## Task Mappings",
    ]
    lines.extend(
        "- {task_id}: {blockers}".format(
            task_id=item["task_id"],
            blockers=",".join(item["blockers_targeted"]),
        )
        for item in payload["task_mappings"]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
