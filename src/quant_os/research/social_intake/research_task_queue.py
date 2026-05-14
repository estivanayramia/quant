from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.research.social_intake.hypothesis_queue import write_hypothesis_queue_report
from quant_os.research.social_intake.task_prioritizer import prioritize_social_research_tasks

REPORT_ROOT = Path("reports/sequence34/research_tasks")


def write_research_task_queue_report(
    *,
    capture_root: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    hypotheses = write_hypothesis_queue_report(capture_root=capture_root, output_root=output_root)
    payload = prioritize_social_research_tasks(hypothesis_queue=hypotheses)
    payload["hypothesis_queue_report_paths"] = hypotheses["report_paths"]
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_research_task_queue.json"
    md_path = root / "latest_research_task_queue.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 34 Social Research Task Queue",
        "",
        "Priority-ranked tasks from social research hypotheses. No social execution logic.",
        "",
        f"Status: {payload['research_task_queue_status']}",
        f"Top priority reason: {payload['top_priority_reason']}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Tasks",
    ]
    lines.extend(
        "- {task_id}: {status}".format(
            task_id=item["task_id"],
            status=item["priority_status"],
        )
        for item in payload["tasks"]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
