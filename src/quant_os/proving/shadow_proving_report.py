from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.proving.shadow_proving_eval import evaluate_shadow_proving
from quant_os.proving.shadow_proving_spec import (
    SHADOW_PROVING_SAFETY,
    write_shadow_proving_spec_report,
)
from quant_os.research.prediction_markets.shadow_execution_report import (
    write_shadow_execution_report,
)

REPORT_ROOT = Path("reports/sequence32/shadow_proving")


def write_shadow_proving_report(
    *,
    output_root: str | Path = ".",
    polymarket_snapshot_path: str | Path | None = None,
    pmxt_manifest_path: str | Path | None = None,
    reference_datasets_manifest_path: str | Path | None = None,
) -> dict[str, Any]:
    spec = write_shadow_proving_spec_report(output_root=output_root)
    shadow_execution = write_shadow_execution_report(
        output_root=output_root,
        polymarket_snapshot_path=polymarket_snapshot_path,
        pmxt_manifest_path=pmxt_manifest_path,
        reference_datasets_manifest_path=reference_datasets_manifest_path,
    )
    payload = {
        "sequence": "32",
        "schema_version": "shadow_proving_report_v1",
        "spec_report_paths": spec["report_paths"],
        **evaluate_shadow_proving(shadow_execution_reports=[shadow_execution]),
        **SHADOW_PROVING_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_shadow_proving_report.json"
    md_path = root / "latest_shadow_proving_report.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 32 Shadow-Proving Report",
        "",
        "Shadow proving evaluation for future tiny canary consideration. No execution authority.",
        "",
        f"Status: {payload['shadow_proving_status']}",
        f"Ready for tiny canary consideration: {payload['ready_for_tiny_canary_consideration']}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Aggregate Metrics",
    ]
    lines.extend(f"- {key}: {value}" for key, value in payload["aggregate_metrics"].items())
    lines.extend(["", "## Blockers"])
    lines.extend(f"- {item}" for item in payload["blockers"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
