from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.proving.shadow_blocker_attribution import attribute_shadow_blockers
from quant_os.proving.shadow_window_report import write_shadow_window_report

REPORT_ROOT = Path("reports/sequence33/blocker_attribution")


def write_shadow_blocker_report(
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
    payload = attribute_shadow_blockers(shadow_windows=windows)
    payload["shadow_window_report_paths"] = windows["report_paths"]
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_blocker_attribution.json"
    md_path = root / "latest_blocker_attribution.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 33 Shadow Blocker Attribution",
        "",
        "Stable blocker attribution across fixture and synthetic stress windows.",
        "",
        f"Status: {payload['blocker_attribution_status']}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Blocker Groups",
    ]
    for group, blockers in payload["blocker_groups"].items():
        lines.append(f"- {group}: {', '.join(blockers) if blockers else 'none'}")
    lines.extend(["", "## Fixability"])
    for group, blockers in payload["fixability"].items():
        lines.append(f"- {group}: {', '.join(blockers) if blockers else 'none'}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
