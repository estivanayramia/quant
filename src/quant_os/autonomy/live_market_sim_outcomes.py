from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from quant_os.autonomy.live_market_sim_common import (
    hash_payload,
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
    public_market_payloads: dict[str, dict[str, Any]] | None = None,
    public_network_ok: bool = False,
) -> dict[str, Any]:
    state = load_state(output_root=output_root)
    ledger = load_json(
        "reports/live_market_sim_profitability/ledger/latest_ledger.json",
        output_root=output_root,
    ) or {}
    public_outcome_labels = public_outcome_labels or {}
    public_market_payloads = public_market_payloads or {}
    outcomes: list[dict[str, Any]] = []
    blockers: list[str] = []
    public_resolution_cache: dict[str, dict[str, Any] | None] = {}
    entries = _merge_entries(
        list(state.get("ledger_entries", []) or []),
        list(ledger.get("ledger_entries", []) or []),
    )
    for entry in entries:
        observation_id = entry.get("observation_id")
        label = public_outcome_labels.get(str(observation_id))
        public_resolution = _public_resolution_for_entry(
            entry,
            public_market_payloads=public_market_payloads,
            public_resolution_cache=public_resolution_cache,
            public_network_ok=public_network_ok,
        )
        if label is None and public_resolution:
            label = public_resolution["outcome_label"]
        if label is None:
            outcomes.append(
                {
                    **_base(entry),
                    "outcome_status": "PENDING",
                    "outcome_label": None,
                    "public_resolution_checked": bool(public_network_ok or public_market_payloads),
                    "public_resolution_source": public_resolution_cache.get(str(entry.get("market_ticker")))
                    or None,
                }
            )
        elif label not in VALID_OUTCOMES:
            blockers.append("GUESSED_OR_INVALID_OUTCOME_LABEL")
            outcomes.append({**_base(entry), "outcome_status": "BLOCKED", "outcome_label": label})
        else:
            outcomes.append(
                {
                    **_base(entry),
                    "outcome_status": "RESOLVED",
                    "outcome_label": label,
                    "public_resolution_source": (
                        public_resolution.get("source_url") if public_resolution else "public_resolution_label"
                    ),
                    "public_resolution": public_resolution,
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
    public_market_payloads: dict[str, dict[str, Any]] | None = None,
    public_network_ok: bool = False,
) -> dict[str, Any]:
    payload = build_live_market_sim_outcomes(
        output_root=output_root,
        public_outcome_labels=public_outcome_labels,
        public_market_payloads=public_market_payloads,
        public_network_ok=public_network_ok,
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


def _public_resolution_for_entry(
    entry: dict[str, Any],
    *,
    public_market_payloads: dict[str, dict[str, Any]],
    public_resolution_cache: dict[str, dict[str, Any] | None],
    public_network_ok: bool,
) -> dict[str, Any] | None:
    ticker = str(entry.get("market_ticker") or "")
    if not ticker:
        return None
    if ticker not in public_resolution_cache:
        payload = public_market_payloads.get(ticker)
        if payload is None and public_network_ok:
            payload = _fetch_public_kalshi_market(ticker)
        public_resolution_cache[ticker] = _resolution_from_public_market_payload(ticker, payload)
    return public_resolution_cache[ticker]


def _fetch_public_kalshi_market(ticker: str) -> dict[str, Any] | None:
    url = f"https://external-api.kalshi.com/trade-api/v2/markets/{ticker}"
    request = Request(url, method="GET", headers={"User-Agent": "quant-os-readonly-outcome-resolver/1.0"})
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, json.JSONDecodeError):
        return None


def _resolution_from_public_market_payload(ticker: str, payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not payload:
        return None
    market = payload.get("market", payload)
    label = str(market.get("result") or "").lower()
    status = str(market.get("status") or "").lower()
    if label not in VALID_OUTCOMES or status not in {"finalized", "settled"}:
        return None
    source_url = str(
        market.get("source_url") or f"https://external-api.kalshi.com/trade-api/v2/markets/{ticker}"
    )
    resolution = {
        "source_kind": "kalshi_public_market_data",
        "source_url": source_url,
        "market_ticker": ticker,
        "market_status": status,
        "outcome_label": label,
        "settlement_ts": market.get("settlement_ts"),
        "expiration_value": market.get("expiration_value"),
        "result": market.get("result"),
        "public_read_only": True,
        "request_method": "GET",
        "authenticated": False,
    }
    resolution["evidence_hash"] = hash_payload(resolution)
    return resolution
