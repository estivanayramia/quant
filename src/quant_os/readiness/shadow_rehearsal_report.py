from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.proving.unblockability_report import write_unblockability_report
from quant_os.readiness.shadow_rehearsal import evaluate_shadow_rehearsal_readiness

REPORT_ROOT = Path("reports/sequence33/shadow_rehearsal")


def write_shadow_rehearsal_report(
    *,
    output_root: str | Path = ".",
    polymarket_snapshot_path: str | Path | None = None,
    pmxt_manifest_path: str | Path | None = None,
    reference_datasets_manifest_path: str | Path | None = None,
) -> dict[str, Any]:
    unblockability = write_unblockability_report(
        output_root=output_root,
        polymarket_snapshot_path=polymarket_snapshot_path,
        pmxt_manifest_path=pmxt_manifest_path,
        reference_datasets_manifest_path=reference_datasets_manifest_path,
    )
    payload = evaluate_shadow_rehearsal_readiness(unblockability=unblockability)
    payload["unblockability_report_paths"] = unblockability["report_paths"]
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_shadow_rehearsal.json"
    md_path = root / "latest_shadow_rehearsal.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 33 Shadow Rehearsal Readiness",
        "",
        "Offline readiness for a later bounded shadow rehearsal. No live readiness.",
        "",
        f"Status: {payload['shadow_rehearsal_status']}",
        f"Ready for bounded shadow rehearsal: {payload['ready_for_bounded_shadow_rehearsal']}",
        f"Ready for live trading: {payload['ready_for_live_trading']}",
        "",
        "## Blockers",
    ]
    lines.extend(f"- {item}" for item in payload["blockers"])
    lines.extend(["", "## Required Before Rehearsal"])
    lines.extend(f"- {item}" for item in payload["required_before_rehearsal"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
