from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.data.prediction_markets.activity_capture import build_activity_dataset_from_capture

REPORT_ROOT = Path("reports/sequence27/reference_context")
REFERENCE_ALIGNMENT_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
}


def build_reference_alignment(dataset: dict[str, Any]) -> dict[str, Any]:
    rows = [_market_reference_alignment(market, dataset=dataset) for market in dataset["markets"]]
    attached_count = sum(1 for row in rows if row["reference_status"] == "ATTACHED_OFFLINE")
    missing_count = sum(1 for row in rows if row["reference_status"] == "MISSING_REFERENCE_CONTEXT")
    aligned_resolved = sum(1 for row in rows if row["alignment_status"] == "ALIGNED_RESOLVED")
    status = (
        "REFERENCE_CONTEXT_ATTACHED_WITH_GAPS"
        if attached_count > 0 and missing_count > 0
        else "REFERENCE_CONTEXT_ATTACHED"
        if attached_count > 0
        else "REFERENCE_CONTEXT_INSUFFICIENT"
    )
    return {
        "sequence": "27",
        "source": dataset["source"],
        "source_mode": dataset["source_mode"],
        "lane_id": dataset["lane_id"],
        "dataset_id": dataset["dataset_id"],
        "dataset_hash": dataset["dataset_hash"],
        "reference_context_status": status,
        "summary": {
            "market_count": len(rows),
            "attached_reference_count": attached_count,
            "missing_reference_count": missing_count,
            "aligned_resolved_count": aligned_resolved,
        },
        "market_reference_alignment": rows,
        "observed_facts": [
            "Reference context is attached from saved offline artifacts only.",
            "Observed lane activity is kept separate from inferred reference alignment.",
        ],
        "inferred_patterns": [
            "Reference alignment can support venue-specific hypotheses, but does not prove edge.",
        ],
        "unknowns": [
            "Missing or weak reference context remains a blocker for strong signal claims.",
        ],
        "internet_required": False,
        **REFERENCE_ALIGNMENT_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_reference_context_report(
    *,
    fixture_path: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    dataset = build_activity_dataset_from_capture(fixture_path)
    payload = build_reference_alignment(dataset)
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _market_reference_alignment(market: dict[str, Any], *, dataset: dict[str, Any]) -> dict[str, Any]:
    context = market.get("reference_context") or {}
    resolution = market.get("resolution") or {}
    activity = market.get("activity") or []
    reference_status = "ATTACHED_OFFLINE" if context else "MISSING_REFERENCE_CONTEXT"
    if not context:
        alignment_status = "MISSING_CONTEXT"
    elif not market["included_in_lane_activity_research"]:
        alignment_status = "EXCLUDED_MARKET"
    elif resolution.get("status") == "RESOLVED":
        alignment_status = "ALIGNED_RESOLVED"
    elif resolution.get("status") == "UNRESOLVED":
        alignment_status = "UNRESOLVED_REFERENCE"
    else:
        alignment_status = str(resolution.get("status") or "UNKNOWN_REFERENCE_STATUS")
    return {
        "market_id": market["market_id"],
        "condition_id": market["condition_id"],
        "slug": market["slug"],
        "lane_id": market["lane_id"],
        "reference_status": reference_status,
        "alignment_status": alignment_status,
        "event_time": context.get("event_time"),
        "reference_id": context.get("reference_id"),
        "reference_source_mode": context.get("source_mode"),
        "resolution_status": resolution.get("status"),
        "label_confidence": resolution.get("confidence"),
        "latest_activity_time": activity[-1]["timestamp"] if activity else None,
        "observed_lane_activity": bool(activity),
        "attached_reference_context": bool(context),
        "inferred_alignment": alignment_status,
        "unknowns": _unknowns(reference_status=reference_status, resolution=resolution),
        "provenance": {
            "source_path": dataset["source_path"],
            "source_sha256": dataset["source_sha256"],
            "dataset_hash": dataset["dataset_hash"],
            "source_mode": dataset["source_mode"],
        },
    }


def _unknowns(*, reference_status: str, resolution: dict[str, Any]) -> list[str]:
    unknowns = []
    if reference_status == "MISSING_REFERENCE_CONTEXT":
        unknowns.append("Reference context is missing from the saved artifact.")
    if resolution.get("confidence") in {"LOW", "UNKNOWN", None}:
        unknowns.append("Resolution/reference confidence is weak or unknown.")
    return unknowns or ["No major reference-context gap recorded in the saved artifact."]


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_reference_context.json"
    md_path = root / "latest_reference_context.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 27 Reference Context",
        "",
        "Research-only reference context report. No execution authority.",
        "",
        f"Lane: {payload['lane_id']}",
        f"Reference context: {payload['reference_context_status']}",
        f"Attached references: {payload['summary']['attached_reference_count']}",
        f"Missing references: {payload['summary']['missing_reference_count']}",
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
