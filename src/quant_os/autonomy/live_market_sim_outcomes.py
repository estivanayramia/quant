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

REPORT_DIR = Path("reports/live_market_sim_profitability/outcomes")
VALID_OUTCOMES = {"yes", "no"}


def build_live_market_sim_outcomes(
    *,
    output_root: str | Path = ".",
    public_outcome_labels: dict[str, str] | None = None,
) -> dict[str, Any]:
    state = load_state(output_root=output_root)
    ledger = load_json(
        "reports/live_market_sim_profitability/ledger/latest_ledger.json",
        output_root=output_root,
    ) or {}
    public_outcome_labels = public_outcome_labels or {}
    outcomes: list[dict[str, Any]] = []
    blockers: list[str] = []
    entries = _merge_entries(
        list(state.get("ledger_entries", []) or []),
        list(ledger.get("ledger_entries", []) or []),
    )
    for entry in entries:
        observation_id = entry.get("observation_id")
        label = public_outcome_labels.get(str(observation_id))
        if label is None:
            outcomes.append({**_base(entry), "outcome_status": "PENDING", "outcome_label": None})
        elif label not in VALID_OUTCOMES:
            blockers.append("GUESSED_OR_INVALID_OUTCOME_LABEL")
            outcomes.append({**_base(entry), "outcome_status": "BLOCKED", "outcome_label": label})
        else:
            outcomes.append(
                {
                    **_base(entry),
                    "outcome_status": "RESOLVED",
                    "outcome_label": label,
                    "public_resolution_source": "public_resolution_label",
                    "guessed_outcome": False,
                }
            )
    resolved = [item for item in outcomes if item["outcome_status"] == "RESOLVED"]
    pending = [item for item in outcomes if item["outcome_status"] == "PENDING"]
    if blockers:
        status = "LIVE_SIM_OUTCOME_BLOCKED"
    elif resolved:
        status = "LIVE_SIM_OUTCOME_RESOLVED"
    else:
        status = "LIVE_SIM_OUTCOME_PENDING"
    return sim_safety_payload(
        schema_version="live_market_sim_outcomes_v1",
        status=status,
        allowed_statuses=["LIVE_SIM_OUTCOME_PENDING", "LIVE_SIM_OUTCOME_RESOLVED", "LIVE_SIM_OUTCOME_BLOCKED"],
        outcomes=outcomes,
        resolved_outcome_count=len(resolved),
        pending_outcome_count=len(pending),
        blockers=blockers,
        next_action="Compute fake PnL from public outcome labels."
        if resolved
        else "Wait for public resolution labels and re-run outcome check.",
    )


def write_live_market_sim_outcomes_report(
    *,
    output_root: str | Path = ".",
    public_outcome_labels: dict[str, str] | None = None,
) -> dict[str, Any]:
    payload = build_live_market_sim_outcomes(
        output_root=output_root,
        public_outcome_labels=public_outcome_labels,
    )
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_outcomes.json",
        md_name="latest_outcomes.md",
        title="Live Market Sim Outcomes",
        summary="Public resolution labels for fake-money live-market simulated positions.",
    )
    write_state(output_root=output_root, outcomes=payload["outcomes"], next_action=payload["next_action"])
    return payload


def _base(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "observation_id": entry.get("observation_id"),
        "market_ticker": entry.get("market_ticker"),
        "fake_client_order_id": entry.get("fake_client_order_id"),
        "fake_fill_id": entry.get("fake_fill_id"),
        "fake_entry_price": entry.get("fake_entry_price"),
        "fake_contracts": entry.get("fake_contracts"),
        "event_hash": entry.get("event_hash"),
    }


def _merge_entries(
    existing: list[dict[str, Any]],
    incoming: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged = list(existing)
    seen = {item.get("ledger_entry_id") or item.get("observation_id") for item in merged}
    for item in incoming:
        key = item.get("ledger_entry_id") or item.get("observation_id")
        if key not in seen:
            merged.append(item)
            seen.add(key)
    return merged
