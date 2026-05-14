from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.research.social_intake.capture_loader import write_capture_inventory
from quant_os.research.social_intake.post_classifier import classify_social_posts

REPORT_ROOT = Path("reports/sequence34/social_intake")


def write_post_classification_report(
    *,
    capture_root: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    inventory = write_capture_inventory(capture_root=capture_root, output_root=output_root)
    payload = classify_social_posts(inventory=inventory)
    payload["capture_inventory_report_paths"] = inventory["report_paths"]
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_post_classification.json"
    md_path = root / "latest_post_classification.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 34 Social Post Classification",
        "",
        "Classification is for research intake only. Social posts are not trade signals.",
        "",
        f"Status: {payload['classification_status']}",
        f"Post count: {payload['post_count']}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Classifications",
    ]
    lines.extend(
        "- {post_id}: {category} ({confidence})".format(
            post_id=item["post_id"],
            category=item["primary_category"],
            confidence=item["confidence"],
        )
        for item in payload["classifications"]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
