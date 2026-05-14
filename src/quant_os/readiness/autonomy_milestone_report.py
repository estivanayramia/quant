from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.readiness.autonomy_milestones import build_autonomy_milestones

REPORT_ROOT = Path("reports/sequence35/autonomy_milestones")


def write_autonomy_milestone_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_autonomy_milestones()
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_autonomy_milestones.json"
    md_path = root / "latest_autonomy_milestones.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 35 Autonomy Milestone Ledger",
        "",
        "Finite path to autonomous orders. Live orders remain blocked.",
        "",
        f"Milestones: {payload['milestone_count']}",
        "Next required milestone: {milestone_id}".format(
            milestone_id=payload["next_required_milestone"]["milestone_id"],
        ),
        f"Live orders allowed: {payload['live_orders_allowed']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Milestones",
    ]
    lines.extend(
        "{index}. {title}: {status} - next: {next_action}".format(
            index=item["milestone_index"],
            title=item["title"],
            status=item["status"],
            next_action=item["required_next_action"],
        )
        for item in payload["milestones"]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
