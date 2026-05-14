from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.proving.shadow_proving_report import write_shadow_proving_report

REPORT_ROOT = Path("reports/sequence32/canary_preconditions")
CANARY_PRECONDITION_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
    "prediction_market_execution_authority_added": False,
}


def write_canary_preconditions_report(
    *,
    output_root: str | Path = ".",
    polymarket_snapshot_path: str | Path | None = None,
    pmxt_manifest_path: str | Path | None = None,
    reference_datasets_manifest_path: str | Path | None = None,
) -> dict[str, Any]:
    proving = write_shadow_proving_report(
        output_root=output_root,
        polymarket_snapshot_path=polymarket_snapshot_path,
        pmxt_manifest_path=pmxt_manifest_path,
        reference_datasets_manifest_path=reference_datasets_manifest_path,
    )
    payload = build_canary_preconditions(proving)
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def build_canary_preconditions(shadow_proving: dict[str, Any]) -> dict[str, Any]:
    shadow_ready = (
        shadow_proving["shadow_proving_status"] == "READY_FOR_TINY_CANARY_CONSIDERATION"
    )
    no_realism_disqualifier = "UNRESOLVED_REALISM_DISQUALIFIER" not in shadow_proving["blockers"]
    still_blocked = _blocked_reasons(
        shadow_ready=shadow_ready,
        no_realism_disqualifier=no_realism_disqualifier,
        shadow_proving=shadow_proving,
    )
    return {
        "sequence": "32",
        "schema_version": "canary_preconditions_v1",
        "canary_preconditions_status": (
            "READY_FOR_TINY_CANARY_CONSIDERATION"
            if not still_blocked
            else "CANARY_PRECONDITIONS_NOT_MET"
        ),
        "ready_for_tiny_canary_consideration": not still_blocked,
        "manual_enablement_required": True,
        "manual_enablement_present": False,
        "tiny_nominal_capital_only": {
            "required": True,
            "max_nominal_usd": "10",
        },
        "hard_max_order_count": 1,
        "hard_max_exposure_usd": "10",
        "immediate_self_disable_triggers": [
            "any_reconciliation_mismatch",
            "any_guard_live_failure",
            "any_unexpected_open_order",
            "any_shadow_proving_regression",
            "any_operator_disable_signal",
        ],
        "reconciliation_required": True,
        "dry_run_parity_required": True,
        "shadow_proving_thresholds_met": shadow_ready,
        "no_unresolved_realism_disqualifier": no_realism_disqualifier,
        "still_blocked_reasons": still_blocked,
        "shadow_proving_status": shadow_proving["shadow_proving_status"],
        "shadow_proving_blockers": shadow_proving["blockers"],
        "observed_facts": [
            "Canary preconditions are a fail-closed record, not an enablement path.",
            "Manual enablement is absent and shadow proving thresholds are not met.",
        ],
        "unknowns": [
            "No tiny real order can be considered until shadow proving becomes stable.",
            "Real canary implementation remains out of scope.",
        ],
        **CANARY_PRECONDITION_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _blocked_reasons(
    *,
    shadow_ready: bool,
    no_realism_disqualifier: bool,
    shadow_proving: dict[str, Any],
) -> list[str]:
    blockers = ["manual_enablement_absent", "real_canary_phase_not_authorized"]
    if not shadow_ready:
        blockers.append("shadow_proving_not_ready")
    if not no_realism_disqualifier:
        blockers.append("unresolved_realism_disqualifier")
    if "WEAK_EVIDENCE_BLOCKS_PROMOTION" in shadow_proving["blockers"]:
        blockers.append("weak_evidence_blocks_promotion")
    if "RISK_BLOCKS_CANARY_CONSIDERATION" in shadow_proving["blockers"]:
        blockers.append("risk_blocks_canary_consideration")
    return blockers


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_canary_preconditions.json"
    md_path = root / "latest_canary_preconditions.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 32 Canary Preconditions",
        "",
        "Fail-closed preconditions before any future tiny real canary consideration.",
        "",
        f"Status: {payload['canary_preconditions_status']}",
        f"Ready for tiny canary consideration: {payload['ready_for_tiny_canary_consideration']}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Still Blocked Reasons",
    ]
    lines.extend(f"- {item}" for item in payload["still_blocked_reasons"])
    lines.extend(["", "## Self-Disable Triggers"])
    lines.extend(f"- {item}" for item in payload["immediate_self_disable_triggers"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
