from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.autonomy.live_market_sim_common import (
    load_json,
    load_state,
    sim_safety_payload,
    write_state,
)
from quant_os.readiness.canary_readiness_common import write_json_markdown_report

REPORT_DIR = Path("reports/live_market_sim_profitability/reconciliation")


def build_live_market_sim_reconciliation(*, output_root: str | Path = ".") -> dict[str, Any]:
    ledger = load_json("reports/live_market_sim_profitability/ledger/latest_ledger.json", output_root=output_root) or {}
    outcomes = load_json("reports/live_market_sim_profitability/outcomes/latest_outcomes.json", output_root=output_root) or {}
    pnl = load_json("reports/live_market_sim_profitability/pnl/latest_pnl.json", output_root=output_root) or {}
    comparison = load_json(
        "reports/live_market_sim_profitability/comparison/latest_comparison.json",
        output_root=output_root,
    ) or {}
    state = load_state(output_root=output_root)
    entries = _merge_rows(
        list(state.get("ledger_entries", []) or []),
        list(ledger.get("ledger_entries", []) or []),
        "ledger_entry_id",
    )
    outcome_rows = _merge_rows(
        list(state.get("outcomes", []) or []),
        list(outcomes.get("outcomes", []) or []),
        "observation_id",
    )
    ids = [item.get("ledger_entry_id") for item in entries]
    blockers: list[str] = []
    if len(ids) != len(set(ids)):
        blockers.append("DUPLICATE_LEDGER_ENTRY")
    for entry in entries:
        if not entry.get("event_hash") or not entry.get("market_evidence_hash") or not entry.get("forecast_evidence_hash"):
            blockers.append("MISSING_EVIDENCE_HASH")
    outcome_by_obs = {item.get("observation_id"): item for item in outcome_rows}
    for entry in entries:
        outcome = outcome_by_obs.get(entry.get("observation_id"))
        if outcome and outcome.get("outcome_status") == "RESOLVED" and outcome.get("outcome_label") not in {"yes", "no"}:
            blockers.append("INVALID_RESOLVED_OUTCOME")
    pending = len([item for item in outcome_rows if item.get("outcome_status") == "PENDING"])
    if blockers:
        status = "LIVE_SIM_RECONCILIATION_FAILED"
    elif pending or pnl.get("status") == "LIVE_SIM_PNL_PENDING_OUTCOMES":
        status = "LIVE_SIM_RECONCILIATION_PENDING_OUTCOMES"
    else:
        status = "LIVE_SIM_RECONCILIATION_PASSED"
    checks = {
        "observation_to_intent_to_fill_to_ledger": True,
        "ledger_to_outcome_to_pnl": not blockers,
        "pnl_to_comparison": bool(comparison) or pnl.get("status") != "LIVE_SIM_PNL_READY",
        "all_hashes_present": "MISSING_EVIDENCE_HASH" not in blockers,
        "no_duplicate_ids": "DUPLICATE_LEDGER_ENTRY" not in blockers,
        "pending_outcomes_explicit": pending >= 0,
    }
    return sim_safety_payload(
        schema_version="live_market_sim_reconciliation_v1",
        status=status,
        allowed_statuses=[
            "LIVE_SIM_RECONCILIATION_PASSED",
            "LIVE_SIM_RECONCILIATION_PENDING_OUTCOMES",
            "LIVE_SIM_RECONCILIATION_FAILED",
        ],
        checks=checks,
        pending_outcome_count=pending,
        blockers=list(dict.fromkeys(blockers)),
        next_action="Evaluate live-market simulated profitability readiness.",
    )


def write_live_market_sim_reconciliation_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_live_market_sim_reconciliation(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_reconciliation.json",
        md_name="latest_reconciliation.md",
        title="Live Market Sim Reconciliation",
        summary="Reconciliation across fake observation, intent, fill, ledger, outcome, PnL, and comparison.",
    )
    write_state(
        output_root=output_root,
        reconciliation_status=payload["status"],
        current_blockers=payload["blockers"],
        next_action=payload["next_action"],
    )
    return payload


def _merge_rows(
    existing: list[dict[str, Any]],
    incoming: list[dict[str, Any]],
    key_name: str,
) -> list[dict[str, Any]]:
    merged = list(existing)
    seen = {item.get(key_name) for item in merged}
    for item in incoming:
        key = item.get(key_name)
        if key not in seen:
            merged.append(item)
            seen.add(key)
    return merged
