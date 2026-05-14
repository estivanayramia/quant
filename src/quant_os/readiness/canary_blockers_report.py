from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.readiness.canary_preconditions_report import (
    CANARY_PRECONDITION_SAFETY,
    write_canary_preconditions_report,
)

REPORT_ROOT = Path("reports/sequence32/canary_blockers")


def write_canary_blockers_report(
    *,
    output_root: str | Path = ".",
    polymarket_snapshot_path: str | Path | None = None,
    pmxt_manifest_path: str | Path | None = None,
    reference_datasets_manifest_path: str | Path | None = None,
) -> dict[str, Any]:
    preconditions = write_canary_preconditions_report(
        output_root=output_root,
        polymarket_snapshot_path=polymarket_snapshot_path,
        pmxt_manifest_path=pmxt_manifest_path,
        reference_datasets_manifest_path=reference_datasets_manifest_path,
    )
    payload = build_canary_blockers(preconditions)
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def build_canary_blockers(preconditions: dict[str, Any]) -> dict[str, Any]:
    categories = _blocker_categories(preconditions)
    return {
        "sequence": "32",
        "schema_version": "canary_blockers_v1",
        "canary_blocker_status": "TINY_CANARY_BLOCKED"
        if categories
        else "NO_CANARY_BLOCKERS_IDENTIFIED",
        "still_blocked": bool(categories),
        "not_almost_ready": bool(categories),
        "blocker_categories": categories,
        "still_blocked_reasons": preconditions["still_blocked_reasons"],
        "canary_preconditions_status": preconditions["canary_preconditions_status"],
        "observed_facts": [
            "Tiny autonomous orders remain blocked.",
            "The blocker report ties the block back to shadow proving and realism evidence.",
        ],
        "inferred_patterns": [
            "The next useful work is more shadow evidence, not real canary enablement.",
        ],
        **CANARY_PRECONDITION_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _blocker_categories(preconditions: dict[str, Any]) -> dict[str, list[str]]:
    proving_blockers = preconditions["shadow_proving_blockers"]
    return {
        "edge_weakness": [
            "No credible positive edge signal has earned shadow promotion.",
            "Weak evidence explicitly blocks promotion.",
        ]
        if "WEAK_EVIDENCE_BLOCKS_PROMOTION" in proving_blockers
        else [],
        "replay_realism_gaps": [
            "Replay design remains partial.",
            "Realism disqualifiers remain unresolved.",
        ]
        if "UNRESOLVED_REALISM_DISQUALIFIER" in proving_blockers
        else [],
        "fill_uncertainty": [
            "Current shadow evidence has zero conservative fills.",
            "Fill sensitivity cannot be trusted with the current sample.",
        ],
        "shadow_sample_too_thin": [
            "Shadow windows and intent count are below proving thresholds.",
        ]
        if (
            "SHADOW_SAMPLE_TOO_THIN" in proving_blockers
            or "SHADOW_WINDOW_SAMPLE_TOO_THIN" in proving_blockers
        )
        else [],
        "risk_envelope_blocks": [
            "Fail-closed shadow risk blocks canary consideration.",
        ]
        if "RISK_BLOCKS_CANARY_CONSIDERATION" in proving_blockers
        else [],
        "manual_controls_absent": [
            "Manual enablement is required and not present.",
            "A real canary phase has not been authorized.",
        ],
    }


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_canary_blockers.json"
    md_path = root / "latest_canary_blockers.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 32 Canary Blockers",
        "",
        "Tiny autonomous orders remain blocked. No execution authority.",
        "",
        f"Status: {payload['canary_blocker_status']}",
        f"Still blocked: {payload['still_blocked']}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Blocker Categories",
    ]
    for category, reasons in payload["blocker_categories"].items():
        lines.append(f"- {category}: {'; '.join(reasons) if reasons else 'None'}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
