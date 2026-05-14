from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.research.social_intake.hypothesis_extractor import extract_social_hypotheses
from quant_os.research.social_intake.post_classification_report import (
    write_post_classification_report,
)

REPORT_ROOT = Path("reports/sequence34/hypothesis_queue")


def write_hypothesis_queue_report(
    *,
    capture_root: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    classifications = write_post_classification_report(
        capture_root=capture_root,
        output_root=output_root,
    )
    payload = extract_social_hypotheses(classifications=classifications)
    payload["classification_report_paths"] = classifications["report_paths"]
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_hypothesis_queue.json"
    md_path = root / "latest_hypothesis_queue.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 34 Social Hypothesis Queue",
        "",
        "Falsifiable research tasks generated from local social artifacts. No trade rules.",
        "",
        f"Status: {payload['hypothesis_queue_status']}",
        f"Hypothesis count: {payload['hypothesis_count']}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Hypotheses",
    ]
    lines.extend(
        "- {hypothesis_id}: {summary}".format(
            hypothesis_id=item["hypothesis_id"],
            summary=item["claim_summary"],
        )
        for item in payload["hypotheses"]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
