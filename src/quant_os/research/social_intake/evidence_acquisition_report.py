from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.research.social_intake.evidence_acquisition_plan import (
    build_evidence_acquisition_plan,
)
from quant_os.research.social_intake.research_task_queue import (
    write_research_task_queue_report,
)

REPORT_ROOT = Path("reports/sequence34/evidence_acquisition")


def write_evidence_acquisition_report(
    *,
    capture_root: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    tasks = write_research_task_queue_report(capture_root=capture_root, output_root=output_root)
    payload = build_evidence_acquisition_plan(task_queue=tasks)
    payload["research_task_report_paths"] = tasks["report_paths"]
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_evidence_plan.json"
    md_path = root / "latest_evidence_plan.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 34 Evidence Acquisition Plan",
        "",
        "Evidence plan from social research intake. Social posts are not signals.",
        "",
        f"Status: {payload['evidence_plan_status']}",
        f"Phase 33 blocker addressed: {payload['phase33_blocker_addressed']}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Data Needed",
    ]
    lines.extend(f"- {item}" for item in payload["data_needed"])
    lines.extend(["", "## Worth Testing"])
    lines.extend(
        "- {source_post_id}: {priority_status}".format(**item)
        for item in payload["hypotheses_worth_testing"]
    )
    lines.extend(["", "## Rejected"])
    lines.extend(f"- {item}" for item in payload["hypotheses_rejected"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
