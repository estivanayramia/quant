from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.data.prediction_markets.activity_capture import build_activity_dataset_from_capture
from quant_os.research.prediction_markets.reference_alignment import build_reference_alignment

REPORT_ROOT = Path("reports/sequence27/reference_quality")
REFERENCE_QUALITY_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
}


def evaluate_reference_quality(
    *,
    dataset: dict[str, Any],
    alignment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    alignment = alignment or build_reference_alignment(dataset)
    rows = alignment["market_reference_alignment"]
    usable = [
        row
        for row in rows
        if row["alignment_status"] == "ALIGNED_RESOLVED"
        and row["label_confidence"] in {"HIGH", "MEDIUM", "LOW"}
    ]
    missing = [row for row in rows if row["reference_status"] == "MISSING_REFERENCE_CONTEXT"]
    weak = [
        row
        for row in rows
        if row["alignment_status"] == "ALIGNED_RESOLVED"
        and row["label_confidence"] in {"LOW", "UNKNOWN", None}
    ]
    warnings = []
    if missing:
        warnings.append("MISSING_REFERENCE_CONTEXT_PRESENT")
    if weak:
        warnings.append("WEAK_REFERENCE_OR_LABEL_CONFIDENCE_PRESENT")
    status = (
        "REFERENCE_CONTEXT_INSUFFICIENT"
        if len(usable) < 20
        else "REFERENCE_CONTEXT_USABLE_WITH_WARNINGS"
        if warnings
        else "REFERENCE_CONTEXT_USABLE"
    )
    return {
        "sequence": "27",
        "source": dataset["source"],
        "source_mode": dataset["source_mode"],
        "lane_id": dataset["lane_id"],
        "dataset_id": dataset["dataset_id"],
        "dataset_hash": dataset["dataset_hash"],
        "reference_quality_status": status,
        "summary": {
            "market_count": len(rows),
            "usable_reference_count": len(usable),
            "missing_reference_count": len(missing),
            "weak_reference_count": len(weak),
            "aligned_resolved_count": alignment["summary"]["aligned_resolved_count"],
        },
        "warnings": warnings,
        "observed_facts": [
            "Reference quality is derived from saved reference context and resolution confidence.",
        ],
        "inferred_patterns": [
            "Reference context is good enough for research diagnostics, but gaps prevent strong claims.",
        ],
        "unknowns": [
            "Reference data is offline-cached and not independently refreshed in CI.",
        ],
        **REFERENCE_QUALITY_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_reference_quality_report(
    *,
    fixture_path: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    dataset = build_activity_dataset_from_capture(fixture_path)
    payload = evaluate_reference_quality(dataset=dataset)
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_reference_quality.json"
    md_path = root / "latest_reference_quality.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 27 Reference Quality",
        "",
        "Research-only reference quality report. No execution authority.",
        "",
        f"Lane: {payload['lane_id']}",
        f"Reference quality: {payload['reference_quality_status']}",
        f"Usable references: {payload['summary']['usable_reference_count']}",
        f"Warnings: {', '.join(payload['warnings'] or ['None'])}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Observed facts",
    ]
    lines.extend(f"- {item}" for item in payload["observed_facts"])
    lines.extend(["", "## Inferred patterns"])
    lines.extend(f"- {item}" for item in payload["inferred_patterns"])
    lines.extend(["", "## Unknowns"])
    lines.extend(f"- {item}" for item in payload["unknowns"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
