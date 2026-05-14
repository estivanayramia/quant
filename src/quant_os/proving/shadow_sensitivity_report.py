from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.proving.shadow_blocker_report import write_shadow_blocker_report
from quant_os.proving.shadow_sensitivity import evaluate_shadow_sensitivity
from quant_os.proving.shadow_window_report import write_shadow_window_report

REPORT_ROOT = Path("reports/sequence33/shadow_sensitivity")


def write_shadow_sensitivity_report(
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
    payload = evaluate_shadow_sensitivity(
        shadow_windows=windows,
        blocker_attribution=attribution,
    )
    payload["shadow_window_report_paths"] = windows["report_paths"]
    payload["blocker_attribution_report_paths"] = attribution["report_paths"]
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_shadow_sensitivity.json"
    md_path = root / "latest_shadow_sensitivity.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 33 Shadow Sensitivity",
        "",
        "Conservative sensitivity analysis for shadow blockers. No execution authority.",
        "",
        f"Status: {payload['shadow_sensitivity_status']}",
        (
            "Blocked robust across assumptions: "
            f"{payload['blocked_state_robust_across_assumptions']}"
        ),
        f"Optimistic assumptions rewarded: {payload['optimistic_assumptions_rewarded']}",
        "",
        "## Variants",
    ]
    lines.extend(
        "- {variant_id}: {result_status}, accepted={accepted}, lenient={lenient}".format(
            variant_id=variant["variant_id"],
            result_status=variant["result_status"],
            accepted=variant["accepted_for_unblocking"],
            lenient=variant["too_lenient_flag"],
        )
        for variant in payload["variants"]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
