from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.proving.relentless_profit_campaign_state import load_campaign_state
from quant_os.research.lane_selection.relentless_profit_campaign_models import CAMPAIGN_SAFETY

REPORT_ROOT = Path("reports/profit_campaign/autonomy_path")


def build_profit_candidate_autonomy_path(
    *,
    campaign_payload: dict[str, Any] | None = None,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    state = campaign_payload.get("state") if campaign_payload else load_campaign_state(output_root=output_root)
    candidate = (state or {}).get("best_candidate_so_far") or {}
    candidate_found = candidate.get("status") == "PAPER_PROFIT_CANDIDATE"
    return {
        "schema_version": "profit_candidate_autonomy_path_v1",
        "status": "AUTONOMY_PATH_READY_FOR_SHADOW_REHEARSAL"
        if candidate_found
        else "AUTONOMY_PATH_BLOCKED_NO_PAPER_PROFIT_CANDIDATE",
        "selected_lane": candidate.get("lane_id"),
        "evidence_summary": candidate,
        "next_gate": "bounded_shadow_rehearsal" if candidate_found else "continue_relentless_campaign",
        "shadow_duration": "14 days minimum after candidate approval",
        "minimum_paper_trades": 30,
        "reconciliation_requirements": [
            "paper decisions match proof-row replay schema",
            "fills reconcile against conservative fill model",
            "costs, spreads, slippage, and missed fills are retained",
        ],
        "kill_switch_requirements": [
            "manual stop remains available",
            "live authority remains false",
            "candidate invalidated by source, cost, fill, baseline, or placebo regression",
        ],
        "risk_envelope": {
            "paper_only": True,
            "max_live_notional": 0,
            "live_orders_allowed": False,
        },
        "manual_approval_required_before_live": True,
        "live_ready": False,
        "canary_ready": False,
        "live_readiness_claimed": False,
        "canary_readiness_claimed": False,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
        **CAMPAIGN_SAFETY,
    }


def write_profit_candidate_autonomy_path(
    *,
    output_root: str | Path = ".",
    campaign_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = build_profit_candidate_autonomy_path(
        campaign_payload=campaign_payload,
        output_root=output_root,
    )
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_autonomy_path.json"
    md_path = root / "latest_autonomy_path.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Profit Candidate Autonomy Path",
        "",
        "Autonomy path is shadow-only until a strict PAPER_PROFIT_CANDIDATE exists.",
        "",
        f"Status: {payload['status']}",
        f"Selected lane: {payload['selected_lane']}",
        f"Next gate: {payload['next_gate']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Execution authority: {payload['execution_authority']}",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
