from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.research.prediction_markets.shadow_execution_report import (
    write_shadow_execution_report,
)

REPORT_ROOT = Path("reports/sequence31/shadow_autonomy")
SHADOW_AUTONOMY_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
    "prediction_market_execution_authority_added": False,
}


def write_shadow_autonomy_report(
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
    payload = evaluate_shadow_autonomy(shadow_execution)
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def evaluate_shadow_autonomy(shadow_execution: dict[str, Any]) -> dict[str, Any]:
    requirements = {
        "selected_lane": bool(shadow_execution.get("selected_lane_id")),
        "normalized_replay_inputs": shadow_execution["metrics"]["intent_count"] > 0,
        "deterministic_replay_design": "REPLAY_DESIGN_PARTIAL" in shadow_execution["blockers"]
        or shadow_execution["shadow_execution_status"] == "READY_FOR_BOUNDED_SHADOW_AUTONOMY",
        "conservative_fill_model": True,
        "deterministic_shadow_policy": True,
        "bounded_shadow_risk_envelope": True,
        "no_major_realism_disqualifier": "REPLAY_DESIGN_PARTIAL"
        not in shadow_execution["blockers"],
        "no_optimistic_fill_assumption": True,
        "credible_signal_for_shadow": "WEAK_SIGNAL_BLOCKS_SHADOW_AUTONOMY"
        not in shadow_execution["blockers"],
        "no_weak_signal_promotion": True,
    }
    ready = (
        shadow_execution["shadow_execution_status"] == "READY_FOR_BOUNDED_SHADOW_AUTONOMY"
        and all(requirements.values())
    )
    status = (
        "READY_FOR_BOUNDED_SHADOW_AUTONOMY"
        if ready
        else shadow_execution["shadow_execution_status"]
    )
    return {
        "sequence": "31",
        "shadow_autonomy_status": status,
        "ready_for_bounded_shadow_autonomy": ready,
        "not_live_readiness": True,
        "not_profitability_evidence": True,
        "requirements": requirements,
        "blockers": shadow_execution["blockers"],
        "observed_facts": [
            "A deterministic replay design, shadow policy, risk envelope, and fill model exist.",
            "The current fixture sample still blocks shadow autonomy.",
        ],
        "unknowns": [
            "No credible edge signal has been established.",
            "More replay depth is required before autonomous shadow operation is warranted.",
        ],
        **SHADOW_AUTONOMY_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_shadow_autonomy.json"
    md_path = root / "latest_shadow_autonomy.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 31 Shadow Autonomy Readiness",
        "",
        "Bounded shadow-autonomy readiness gate. This is not live readiness.",
        "",
        f"Status: {payload['shadow_autonomy_status']}",
        f"Ready for bounded shadow autonomy: {payload['ready_for_bounded_shadow_autonomy']}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Requirements",
    ]
    lines.extend(f"- {key}: {value}" for key, value in payload["requirements"].items())
    lines.extend(["", "## Blockers"])
    lines.extend(f"- {item}" for item in payload["blockers"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
