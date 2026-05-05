from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.autonomy.proving_health import evaluate_sequence2_readiness


def write_sequence2_readiness_report(
    *,
    walk_forward_summary: dict[str, Any] | None = None,
    proving_summary: dict[str, Any] | None = None,
    validation_summary: dict[str, Any] | None = None,
    realism_summary: dict[str, Any] | None = None,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    root = Path(output_root)
    walk_forward_summary = walk_forward_summary or _load_json(
        root / "reports" / "sequence2" / "walk_forward" / "latest_walk_forward.json"
    )
    proving_summary = proving_summary or _load_json(
        root / "reports" / "sequence2" / "proving" / "latest_proving_summary.json"
    )
    validation_summary = validation_summary or _load_json(
        root / "reports" / "validation" / "latest_summary.json"
    )
    realism_summary = realism_summary or _load_json(
        root / "reports" / "sequence2" / "replay_realism" / "latest_realism_report.json"
    )
    payload = evaluate_sequence2_readiness(
        walk_forward_summary=walk_forward_summary,
        proving_summary=proving_summary,
        validation_summary=validation_summary,
        realism_summary=realism_summary,
    )
    report_root = root / "reports" / "sequence2" / "readiness"
    report_root.mkdir(parents=True, exist_ok=True)
    (report_root / "latest_readiness.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    lines = [
        "# Sequence 2 Readiness",
        "",
        "Evidence summary only. This does not enable live trading.",
        "",
        f"Status: {payload['status']}",
        f"Live allowed: {payload['live_allowed']}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Blockers",
    ]
    lines.extend(f"- {item}" for item in (payload["blockers"] or ["None"]))
    lines.extend(["", "## Warnings"])
    lines.extend(f"- {item}" for item in (payload["warnings"] or ["None"]))
    (report_root / "latest_readiness.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    payload["report_paths"] = {
        "json": str(report_root / "latest_readiness.json"),
        "markdown": str(report_root / "latest_readiness.md"),
    }
    return payload


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None
