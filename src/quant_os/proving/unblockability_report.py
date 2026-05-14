from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.proving.shadow_blocker_report import write_shadow_blocker_report
from quant_os.proving.shadow_sensitivity_report import write_shadow_sensitivity_report
from quant_os.proving.shadow_window_report import write_shadow_window_report
from quant_os.proving.unblockability import evaluate_unblockability

REPORT_ROOT = Path("reports/sequence33/unblockability")


def write_unblockability_report(
    *,
    output_root: str | Path = ".",
    polymarket_snapshot_path: str | Path | None = None,
    pmxt_manifest_path: str | Path | None = None,
    reference_datasets_manifest_path: str | Path | None = None,
) -> dict[str, Any]:
    windows = write_shadow_window_report(
        output_root=output_root,
        polymarket_snapshot_path=polymarket_snapshot_path,
        pmxt_manifest_path=pmxt_manifest_path,
        reference_datasets_manifest_path=reference_datasets_manifest_path,
    )
    attribution = write_shadow_blocker_report(
        output_root=output_root,
        polymarket_snapshot_path=polymarket_snapshot_path,
        pmxt_manifest_path=pmxt_manifest_path,
        reference_datasets_manifest_path=reference_datasets_manifest_path,
    )
    sensitivity = write_shadow_sensitivity_report(
        output_root=output_root,
        polymarket_snapshot_path=polymarket_snapshot_path,
        pmxt_manifest_path=pmxt_manifest_path,
        reference_datasets_manifest_path=reference_datasets_manifest_path,
    )
    payload = evaluate_unblockability(
        shadow_windows=windows,
        blocker_attribution=attribution,
        sensitivity=sensitivity,
    )
    payload["shadow_window_report_paths"] = windows["report_paths"]
    payload["blocker_attribution_report_paths"] = attribution["report_paths"]
    payload["sensitivity_report_paths"] = sensitivity["report_paths"]
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_unblockability.json"
    md_path = root / "latest_unblockability.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 33 Unblockability",
        "",
        "Determines whether bounded shadow autonomy can be unblocked. No execution authority.",
        "",
        f"Status: {payload['unblockability_status']}",
        f"Ready for bounded shadow rehearsal: {payload['ready_for_bounded_shadow_rehearsal']}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Secondary Blockers",
    ]
    lines.extend(f"- {item}" for item in payload["secondary_blockers"])
    lines.extend(["", "## Diagnosis", payload["diagnosis"]])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
