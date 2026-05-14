from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.proving.shadow_proving_report import write_shadow_proving_report
from quant_os.proving.shadow_sample_expansion import build_shadow_sample_windows
from quant_os.research.prediction_markets.shadow_execution_report import (
    write_shadow_execution_report,
)

REPORT_ROOT = Path("reports/sequence33/shadow_samples")


def write_shadow_window_report(
    *,
    output_root: str | Path = ".",
    polymarket_snapshot_path: str | Path | None = None,
    pmxt_manifest_path: str | Path | None = None,
    reference_datasets_manifest_path: str | Path | None = None,
) -> dict[str, Any]:
    shadow_execution = write_shadow_execution_report(
        output_root=output_root,
        polymarket_snapshot_path=polymarket_snapshot_path,
        pmxt_manifest_path=pmxt_manifest_path,
        reference_datasets_manifest_path=reference_datasets_manifest_path,
    )
    shadow_proving = write_shadow_proving_report(
        output_root=output_root,
        polymarket_snapshot_path=polymarket_snapshot_path,
        pmxt_manifest_path=pmxt_manifest_path,
        reference_datasets_manifest_path=reference_datasets_manifest_path,
    )
    payload = build_shadow_sample_windows(
        shadow_execution=shadow_execution,
        shadow_proving=shadow_proving,
    )
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_shadow_windows.json"
    md_path = root / "latest_shadow_windows.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 33 Shadow Sample Windows",
        "",
        "Deterministic fixture and synthetic stress windows. No execution authority.",
        "",
        f"Status: {payload['shadow_sample_status']}",
        f"Total windows: {payload['total_window_count']}",
        f"Proving-effective windows: {payload['proving_effective_window_count']}",
        "",
        "## Evidence Classes",
    ]
    lines.extend(
        f"- {name}: {count}" for name, count in payload["evidence_class_counts"].items()
    )
    lines.extend(["", "## Windows"])
    lines.extend(
        "- {window_id}: {evidence_class}, counts={counts}, edge_proof={proof}".format(
            window_id=window["window_id"],
            evidence_class=window["evidence_class"],
            counts=window["counts_for_proving_thresholds"],
            proof=window["profitability_evidence"],
        )
        for window in payload["windows"]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
