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

REPORT_DIR = Path("reports/live_market_sim_profitability/pnl")


def build_live_market_sim_pnl(*, output_root: str | Path = ".") -> dict[str, Any]:
    outcomes_payload = load_json(
        "reports/live_market_sim_profitability/outcomes/latest_outcomes.json",
        output_root=output_root,
    ) or {}
    state = load_state(output_root=output_root)
    outcomes = _merge_outcomes(
        list(state.get("outcomes", []) or []),
        list(outcomes_payload.get("outcomes", []) or []),
    )
    blockers: list[str] = []
    if outcomes_payload.get("status") == "LIVE_SIM_OUTCOME_BLOCKED":
        blockers.extend(outcomes_payload.get("blockers", []) or ["OUTCOME_BLOCKED"])
    rows = []
    gross = 0.0
    net = 0.0
    pending = 0
    resolved = 0
    resolved_fill_count_by_market: dict[str, int] = {}
    pnl_by_market: dict[str, float] = {}
    proof_rows = []
    proof_gross = 0.0
    proof_net = 0.0
    proof_markets_seen: set[str] = set()
    for outcome in outcomes:
        if outcome.get("outcome_status") == "PENDING":
            pending += 1
            continue
        if outcome.get("outcome_status") != "RESOLVED":
            continue
        resolved += 1
        entry_price = float(outcome.get("fake_entry_price") or 0.0)
        contracts = int(outcome.get("fake_contracts") or 0)
        if outcome.get("outcome_label") == "yes":
            realized = (1.0 - entry_price) * contracts
        elif outcome.get("outcome_label") == "no":
            realized = -entry_price * contracts
        else:
            blockers.append("GUESSED_OR_INVALID_OUTCOME_LABEL")
            continue
        conservative_cost = 0.03 * contracts
        rows.append({**outcome, "fake_gross_pnl": round(realized, 6), "fake_net_pnl": round(realized - conservative_cost, 6)})
        gross += realized
        net += realized - conservative_cost
        market = str(outcome.get("market_ticker") or "UNKNOWN")
        resolved_fill_count_by_market[market] = resolved_fill_count_by_market.get(market, 0) + 1
        pnl_by_market[market] = pnl_by_market.get(market, 0.0) + realized - conservative_cost
        if market not in proof_markets_seen:
            proof_markets_seen.add(market)
            proof_rows.append(rows[-1])
            proof_gross += realized
            proof_net += realized - conservative_cost
    if blockers:
        status = "LIVE_SIM_PNL_BLOCKED"
    elif pending:
        status = "LIVE_SIM_PNL_PENDING_OUTCOMES"
    else:
        status = "LIVE_SIM_PNL_READY"
    return sim_safety_payload(
        schema_version="live_market_sim_pnl_v1",
        status=status,
        allowed_statuses=["LIVE_SIM_PNL_READY", "LIVE_SIM_PNL_PENDING_OUTCOMES", "LIVE_SIM_PNL_BLOCKED"],
        pnl_rows=rows,
        fake_gross_pnl=round(gross, 6),
        fake_net_pnl=round(net, 6),
        proof_gross_pnl=round(proof_gross, 6),
        proof_net_pnl=round(proof_net, 6),
        proof_pnl_rows=proof_rows,
        resolved_outcome_count=resolved,
        pending_outcome_count=pending,
        unique_resolved_market_count=len(resolved_fill_count_by_market),
        unique_resolution_event_count=len(resolved_fill_count_by_market),
        resolved_fill_count_by_market=dict(sorted(resolved_fill_count_by_market.items())),
        pnl_by_market={key: round(value, 6) for key, value in sorted(pnl_by_market.items())},
        proof_resolved_market_count=len(proof_markets_seen),
        proof_resolved_fill_count_by_market={key: 1 for key in sorted(proof_markets_seen)},
        duplicate_resolved_fill_count_excluded_from_proof=max(resolved - len(proof_markets_seen), 0),
        proof_max_single_market_resolved_fill_share=round(1 / len(proof_markets_seen), 6)
        if proof_markets_seen
        else 0.0,
        max_single_market_resolved_fill_share=round(
            max(resolved_fill_count_by_market.values()) / resolved,
            6,
        )
        if resolved
        else 0.0,
        blockers=list(dict.fromkeys(blockers)),
        next_action="Run baseline/placebo comparison." if status == "LIVE_SIM_PNL_READY" else "Continue public outcome checks.",
    )


def write_live_market_sim_pnl_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_live_market_sim_pnl(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_pnl.json",
        md_name="latest_pnl.md",
        title="Live Market Sim PnL",
        summary="Fake PnL from public outcome labels only. Pending outcomes are not realized.",
    )
    write_state(
        output_root=output_root,
        fake_gross_pnl=payload["fake_gross_pnl"],
        fake_net_pnl=payload["fake_net_pnl"],
        next_action=payload["next_action"],
        current_blockers=payload["blockers"],
    )
    return payload


def _merge_outcomes(
    existing: list[dict[str, Any]],
    incoming: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged = list(existing)
    seen = {item.get("observation_id") for item in merged}
    for item in incoming:
        key = item.get("observation_id")
        if key not in seen:
            merged.append(item)
            seen.add(key)
        else:
            merged = [item if row.get("observation_id") == key else row for row in merged]
    return merged
