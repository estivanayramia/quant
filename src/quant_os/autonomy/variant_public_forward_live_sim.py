from __future__ import annotations

import json
import urllib.parse
import urllib.request
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_os.research.strategy_factory.campaign_common import (
    load_report,
    safe_payload,
    write_json_md,
)

KRAKEN_DEPTH_URL = "https://api.kraken.com/0/public/Depth"
KRAKEN_PAIRS = {
    "BTC/USD": "XXBTZUSD",
    "ETH/USD": "XETHZUSD",
    "SOL/USD": "SOLUSD",
    "XRP/USD": "XXRPZUSD",
}


def build_variant_public_forward_live_sim_summary(
    *,
    candidate: dict[str, Any] | None = None,
    observation_count: int = 0,
    eligible_intent_count: int = 0,
    completed_mark_count: int = 0,
    fake_net_pnl: float = 0.0,
) -> dict[str, Any]:
    candidate = candidate or {}
    return safe_payload(
        status="VARIANT_PUBLIC_FORWARD_LIVE_SIM_PENDING",
        selected_strategy_id=candidate.get("id"),
        selected_strategy_family=candidate.get("family"),
        selected_strategy_assets=candidate.get("assets", []),
        observation_count=observation_count,
        eligible_intent_count=eligible_intent_count,
        fake_fill_count=0,
        completed_mark_count=completed_mark_count,
        fake_net_pnl=round(fake_net_pnl, 8),
        data_sources=["kraken_public_rest_unauthenticated_forward_pending"],
        evidence_source="public_forward_live_sim_pending",
        public_forward_evidence_proven=False,
        public_unauthenticated_data_only=True,
        fake_money_only=True,
        no_credentials=True,
        no_orders=True,
        next_action="Collect candidate-matched public forward observations, intents, fills, and future marks.",
    )


def write_variant_public_forward_live_sim_summary(
    *,
    output_root: str | Path = ".",
    candidate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    tournament = load_report(
        output_root=output_root,
        report_dir="tournament",
        json_name="latest_tournament.json",
    )
    payload = build_variant_public_forward_live_sim_summary(
        candidate=candidate or tournament.get("current_best_candidate"),
    )
    return write_json_md(
        payload,
        output_root=output_root,
        report_dir="live_sim",
        json_name="latest_live_sim_summary.json",
        md_name="latest_live_sim_summary.md",
        title="Variant Public Forward Live Sim Summary",
        lines=[
            f"Status: {payload['status']}",
            f"Selected strategy: {payload['selected_strategy_id']}",
            f"Fake net PnL: {payload['fake_net_pnl']}",
            "No live orders, auth, credentials, or signing.",
        ],
    )


def append_variant_public_forward_observations(
    *,
    output_root: str | Path = ".",
    observations: Iterable[dict[str, Any]],
    candidate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    tournament = load_report(
        output_root=output_root,
        report_dir="tournament",
        json_name="latest_tournament.json",
    )
    selected_candidate = candidate or tournament.get("current_best_candidate") or {}
    previous = load_report(
        output_root=output_root,
        report_dir="live_sim",
        json_name="latest_live_sim_summary.json",
    )
    existing_observations = list(previous.get("public_forward_observations") or [])
    incoming = [_normalize_observation(row) for row in observations]
    all_observations = [*existing_observations, *incoming]
    data_sources = sorted({str(row.get("source")) for row in all_observations if row.get("source")})
    payload = build_variant_public_forward_live_sim_summary(
        candidate=selected_candidate,
        observation_count=len(all_observations),
    )
    payload.update(
        public_forward_observations=all_observations,
        data_sources=data_sources,
        source_sample_hashes=[str(row.get("evidence_hash")) for row in all_observations[:25]],
    )
    return write_json_md(
        payload,
        output_root=output_root,
        report_dir="live_sim",
        json_name="latest_live_sim_summary.json",
        md_name="latest_live_sim_summary.md",
        title="Variant Public Forward Live Sim Summary",
        lines=[
            f"Status: {payload['status']}",
            f"Selected strategy: {payload['selected_strategy_id']}",
            f"Observations: {payload['observation_count']}",
            "No live orders, auth, credentials, or signing.",
        ],
    )


def append_variant_public_forward_snapshot(
    *,
    output_root: str | Path = ".",
    public_snapshot: dict[str, Any],
    candidate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    tournament = load_report(
        output_root=output_root,
        report_dir="tournament",
        json_name="latest_tournament.json",
    )
    selected_candidate = candidate or tournament.get("current_best_candidate") or {}
    selected_assets = set(selected_candidate.get("assets") or [])
    source = str(public_snapshot.get("source") or "public_forward_unknown")
    timestamp = str(public_snapshot.get("fetched_at") or "")
    observations: list[dict[str, Any]] = []
    for asset, payload in sorted((public_snapshot.get("symbols") or {}).items()):
        if selected_assets and asset not in selected_assets:
            continue
        book = payload.get("book") or {}
        observations.append(
            {
                "asset": asset,
                "bid": float(book.get("bid") or 0.0),
                "ask": float(book.get("ask") or 0.0),
                "source": source,
                "timestamp": timestamp,
            }
        )
    return append_variant_public_forward_observations(
        output_root=output_root,
        observations=observations,
        candidate=selected_candidate,
    )


def append_variant_public_forward_public_snapshot(
    *,
    output_root: str | Path = ".",
    public_network_ok: bool = False,
    public_snapshot: dict[str, Any] | None = None,
    candidate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    collection_blockers: list[str] = []
    if public_snapshot is None:
        if public_network_ok:
            public_snapshot = fetch_kraken_public_forward_snapshot(candidate=candidate)
        else:
            public_snapshot = {
                "source": "public_forward_network_disabled",
                "fetched_at": "",
                "symbols": {},
            }
            collection_blockers.append("PUBLIC_NETWORK_NOT_ENABLED")
    payload = append_variant_public_forward_snapshot(
        output_root=output_root,
        public_snapshot=public_snapshot,
        candidate=candidate,
    )
    payload["collection_blockers"] = collection_blockers
    return write_json_md(
        payload,
        output_root=output_root,
        report_dir="live_sim",
        json_name="latest_live_sim_summary.json",
        md_name="latest_live_sim_summary.md",
        title="Variant Public Forward Live Sim Summary",
        lines=[
            f"Status: {payload['status']}",
            f"Selected strategy: {payload['selected_strategy_id']}",
            f"Observations: {payload['observation_count']}",
            f"Collection blockers: {', '.join(collection_blockers) if collection_blockers else 'None'}",
            "No live orders, auth, credentials, or signing.",
        ],
    )


def fetch_kraken_public_forward_snapshot(
    *,
    candidate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    symbols: dict[str, Any] = {}
    selected_assets = list((candidate or {}).get("assets") or KRAKEN_PAIRS)
    for asset in selected_assets:
        pair = KRAKEN_PAIRS.get(str(asset))
        if pair is None:
            continue
        try:
            symbols[str(asset)] = {"book": _fetch_kraken_book(pair)}
        except (OSError, TimeoutError, ValueError):
            continue
    return {
        "source": "kraken_public_rest_unauthenticated_forward",
        "fetched_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "symbols": symbols,
    }


def _normalize_observation(row: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "asset": str(row.get("asset") or ""),
        "bid": float(row.get("bid") or 0.0),
        "ask": float(row.get("ask") or 0.0),
        "source": str(row.get("source") or "public_forward_unknown"),
        "timestamp": str(row.get("timestamp") or ""),
    }
    payload["evidence_hash"] = _stable_hash(payload)
    return payload


def _stable_hash(payload: dict[str, Any]) -> str:
    import hashlib
    import json

    raw = json.dumps(payload, sort_keys=True, default=str)
    return "pfobs_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _fetch_kraken_book(pair: str) -> dict[str, float]:
    params = urllib.parse.urlencode({"pair": pair, "count": 1})
    with urllib.request.urlopen(f"{KRAKEN_DEPTH_URL}?{params}", timeout=20) as response:
        data = json.loads(response.read().decode("utf-8"))
    result = data.get("result", {})
    book = next(iter(result.values()), {})
    bid = float(book.get("bids", [[0.0, 0.0]])[0][0])
    ask = float(book.get("asks", [[0.0, 0.0]])[0][0])
    return {
        "bid": bid,
        "ask": ask,
        "bid_size": float(book.get("bids", [[0.0, 0.0]])[0][1]),
        "ask_size": float(book.get("asks", [[0.0, 0.0]])[0][1]),
    }
