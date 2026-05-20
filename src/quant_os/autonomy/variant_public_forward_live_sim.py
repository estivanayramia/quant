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
    fake_fill_count: int = 0,
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
        fake_fill_count=fake_fill_count,
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


def write_variant_public_forward_intents_report(
    *,
    output_root: str | Path = ".",
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
    observations = list(previous.get("public_forward_observations") or [])
    intents = [
        _build_public_forward_intent(
            index=index,
            candidate=selected_candidate,
            observation=observation,
        )
        for index, observation in enumerate(observations)
        if observation.get("asset") in set(selected_candidate.get("assets") or [observation.get("asset")])
    ]
    payload = safe_payload(
        status="VARIANT_PUBLIC_FORWARD_INTENTS_READY",
        selected_strategy_id=selected_candidate.get("id"),
        selected_strategy_family=selected_candidate.get("family"),
        selected_strategy_assets=selected_candidate.get("assets", []),
        eligible_intent_count=len(intents),
        intents=intents,
        fake_money=True,
        no_transmit=True,
        public_forward_evidence_proven=False,
        evidence_source="public_forward_live_sim_pending",
        data_sources=previous.get("data_sources", []),
        no_credentials=True,
        no_orders=True,
    )
    write_json_md(
        payload,
        output_root=output_root,
        report_dir="live_sim",
        json_name="latest_public_forward_intents.json",
        md_name="latest_public_forward_intents.md",
        title="Variant Public Forward Intents",
        lines=[
            f"Status: {payload['status']}",
            f"Selected strategy: {payload['selected_strategy_id']}",
            f"Eligible intents: {payload['eligible_intent_count']}",
            "Fake-money, no-transmit, unsigned intent previews only.",
        ],
    )
    summary = build_variant_public_forward_live_sim_summary(
        candidate=selected_candidate,
        observation_count=len(observations),
        eligible_intent_count=len(intents),
        completed_mark_count=int(previous.get("completed_mark_count") or 0),
        fake_net_pnl=float(previous.get("fake_net_pnl") or 0.0),
    )
    summary.update(
        public_forward_observations=observations,
        data_sources=previous.get("data_sources", []),
        source_sample_hashes=previous.get("source_sample_hashes", []),
        public_forward_intent_hashes=[intent["intent_id"] for intent in intents[:25]],
    )
    write_json_md(
        summary,
        output_root=output_root,
        report_dir="live_sim",
        json_name="latest_live_sim_summary.json",
        md_name="latest_live_sim_summary.md",
        title="Variant Public Forward Live Sim Summary",
        lines=[
            f"Status: {summary['status']}",
            f"Selected strategy: {summary['selected_strategy_id']}",
            f"Observations: {summary['observation_count']}",
            f"Eligible intents: {summary['eligible_intent_count']}",
            "No live orders, auth, credentials, or signing.",
        ],
    )
    return payload


def write_variant_public_forward_fills_and_marks_report(
    *,
    output_root: str | Path = ".",
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
    intents_report = load_report(
        output_root=output_root,
        report_dir="live_sim",
        json_name="latest_public_forward_intents.json",
    )
    observations = list(previous.get("public_forward_observations") or [])
    intents = list(intents_report.get("intents") or [])
    fake_fills: list[dict[str, Any]] = []
    mark_rows: list[dict[str, Any]] = []
    for index, intent in enumerate(intents):
        future_observation = _find_future_observation(intent=intent, observations=observations)
        if future_observation is None:
            continue
        fill, mark = _build_public_forward_fill_and_mark(
            index=index,
            intent=intent,
            future_observation=future_observation,
        )
        fake_fills.append(fill)
        mark_rows.append(mark)
    fake_net_pnl = round(sum(float(row["net_pnl"]) for row in mark_rows), 8)
    lookahead_detected = any(
        str(row["mark_timestamp"]) <= str(row["entry_timestamp"]) for row in mark_rows
    )
    payload = safe_payload(
        status="VARIANT_PUBLIC_FORWARD_FILLS_AND_MARKS_READY",
        selected_strategy_id=selected_candidate.get("id"),
        selected_strategy_family=selected_candidate.get("family"),
        selected_strategy_assets=selected_candidate.get("assets", []),
        fake_fills=fake_fills,
        mark_rows=mark_rows,
        fake_fill_count=len(fake_fills),
        completed_mark_count=len(mark_rows),
        fake_net_pnl=fake_net_pnl,
        lookahead_detected=lookahead_detected,
        public_forward_evidence_proven=False,
        evidence_source="public_forward_live_sim_pending",
        data_sources=previous.get("data_sources", []),
        fake_money=True,
        no_transmit=True,
        no_credentials=True,
        no_orders=True,
    )
    write_json_md(
        payload,
        output_root=output_root,
        report_dir="live_sim",
        json_name="latest_public_forward_fills_and_marks.json",
        md_name="latest_public_forward_fills_and_marks.md",
        title="Variant Public Forward Fills And Marks",
        lines=[
            f"Status: {payload['status']}",
            f"Selected strategy: {payload['selected_strategy_id']}",
            f"Fake fills: {payload['fake_fill_count']}",
            f"Completed future marks: {payload['completed_mark_count']}",
            f"Fake net PnL: {payload['fake_net_pnl']}",
            "Fake-money, no-transmit fills and future public marks only.",
        ],
    )
    summary = build_variant_public_forward_live_sim_summary(
        candidate=selected_candidate,
        observation_count=len(observations),
        eligible_intent_count=int(previous.get("eligible_intent_count") or len(intents)),
        fake_fill_count=len(fake_fills),
        completed_mark_count=len(mark_rows),
        fake_net_pnl=fake_net_pnl,
    )
    summary.update(
        public_forward_observations=observations,
        data_sources=previous.get("data_sources", []),
        source_sample_hashes=previous.get("source_sample_hashes", []),
        public_forward_intent_hashes=previous.get("public_forward_intent_hashes", []),
        public_forward_fill_hashes=[row["fill_id"] for row in fake_fills[:25]],
        public_forward_mark_hashes=[row["mark_id"] for row in mark_rows[:25]],
    )
    write_json_md(
        summary,
        output_root=output_root,
        report_dir="live_sim",
        json_name="latest_live_sim_summary.json",
        md_name="latest_live_sim_summary.md",
        title="Variant Public Forward Live Sim Summary",
        lines=[
            f"Status: {summary['status']}",
            f"Selected strategy: {summary['selected_strategy_id']}",
            f"Observations: {summary['observation_count']}",
            f"Eligible intents: {summary['eligible_intent_count']}",
            f"Fake fills: {summary['fake_fill_count']}",
            f"Completed marks: {summary['completed_mark_count']}",
            "No live orders, auth, credentials, or signing.",
        ],
    )
    return payload


def write_variant_public_forward_collection_cycle(
    *,
    output_root: str | Path = ".",
    public_network_ok: bool = False,
    public_snapshot: dict[str, Any] | None = None,
    candidate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    observation_summary = append_variant_public_forward_public_snapshot(
        output_root=output_root,
        public_network_ok=public_network_ok,
        public_snapshot=public_snapshot,
        candidate=candidate,
    )
    intents = write_variant_public_forward_intents_report(
        output_root=output_root,
        candidate=candidate,
    )
    fills_marks = write_variant_public_forward_fills_and_marks_report(
        output_root=output_root,
        candidate=candidate,
    )
    from quant_os.proving.thousand_strategy_public_forward_evidence import (
        write_thousand_strategy_public_forward_evidence_report,
    )

    evidence = write_thousand_strategy_public_forward_evidence_report(output_root=output_root)
    payload = safe_payload(
        status="VARIANT_PUBLIC_FORWARD_COLLECTION_CYCLE_CHECKPOINTED",
        selected_strategy_id=fills_marks.get("selected_strategy_id"),
        selected_strategy_family=fills_marks.get("selected_strategy_family"),
        selected_strategy_assets=fills_marks.get("selected_strategy_assets", []),
        observation_count=observation_summary.get("observation_count", 0),
        eligible_intent_count=intents.get("eligible_intent_count", 0),
        fake_fill_count=fills_marks.get("fake_fill_count", 0),
        completed_mark_count=fills_marks.get("completed_mark_count", 0),
        fake_net_pnl=fills_marks.get("fake_net_pnl", 0.0),
        public_forward_evidence_status=evidence.get("status"),
        public_forward_evidence_proven=False,
        evidence_blockers=evidence.get("blockers", []),
        collection_blockers=observation_summary.get("collection_blockers", []),
        data_sources=observation_summary.get("data_sources", []),
        fake_money=True,
        no_transmit=True,
        no_credentials=True,
        no_orders=True,
        next_action="Continue append-only public-forward observation/fill/mark collection.",
    )
    return write_json_md(
        payload,
        output_root=output_root,
        report_dir="live_sim",
        json_name="latest_public_forward_cycle.json",
        md_name="latest_public_forward_cycle.md",
        title="Variant Public Forward Collection Cycle",
        lines=[
            f"Status: {payload['status']}",
            f"Selected strategy: {payload['selected_strategy_id']}",
            f"Observations: {payload['observation_count']}",
            f"Eligible intents: {payload['eligible_intent_count']}",
            f"Fake fills: {payload['fake_fill_count']}",
            f"Completed marks: {payload['completed_mark_count']}",
            f"Public-forward evidence: {payload['public_forward_evidence_status']}",
            "Append-only, fake-money, no-transmit public-data collection.",
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


def _build_public_forward_intent(
    *,
    index: int,
    candidate: dict[str, Any],
    observation: dict[str, Any],
) -> dict[str, Any]:
    side = "buy" if index % 2 == 0 else "sell"
    price = float(observation.get("ask") if side == "buy" else observation.get("bid") or 0.0)
    payload = {
        "variant_id": candidate.get("id"),
        "family": candidate.get("family"),
        "timestamp": str(observation.get("timestamp") or ""),
        "asset": str(observation.get("asset") or ""),
        "side": side,
        "reference_price": round(price, 8),
        "notional_usd": 1.0,
        "source_observation_hash": observation.get("evidence_hash"),
        "fake_money": True,
        "no_transmit": True,
        "contains_signed_headers": False,
        "endpoint": "/public/market-data/forward-intent-preview",
    }
    payload["intent_id"] = _stable_hash({"intent": payload, "index": index}).replace(
        "pfobs_",
        "pfint_",
        1,
    )
    return payload


def _find_future_observation(
    *,
    intent: dict[str, Any],
    observations: list[dict[str, Any]],
) -> dict[str, Any] | None:
    asset = str(intent.get("asset") or "")
    timestamp = str(intent.get("timestamp") or "")
    future_rows = [
        row
        for row in observations
        if str(row.get("asset") or "") == asset and str(row.get("timestamp") or "") > timestamp
    ]
    return sorted(future_rows, key=lambda row: str(row.get("timestamp") or ""))[0] if future_rows else None


def _build_public_forward_fill_and_mark(
    *,
    index: int,
    intent: dict[str, Any],
    future_observation: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    side = str(intent.get("side") or "buy")
    entry_price = float(intent.get("reference_price") or 0.0)
    mark_price = float(
        future_observation.get("bid") if side == "buy" else future_observation.get("ask") or 0.0
    )
    notional = float(intent.get("notional_usd") or 0.0)
    quantity = round(notional / entry_price, 12) if entry_price > 0 else 0.0
    gross = (mark_price - entry_price) * quantity
    if side == "sell":
        gross = (entry_price - mark_price) * quantity
    fee_cost = round(notional * 0.0008, 8)
    spread_cost = round(notional * 0.0006, 8)
    slippage_cost = round(notional * 0.0006, 8)
    net_pnl = round(gross - fee_cost - spread_cost - slippage_cost, 8)
    fill_seed = {"intent_id": intent.get("intent_id"), "future": future_observation, "index": index}
    fill_id = _stable_hash({"fill": fill_seed}).replace("pfobs_", "pffill_", 1)
    mark_id = _stable_hash({"mark": fill_seed}).replace("pfobs_", "pfmark_", 1)
    fill = {
        "fill_id": fill_id,
        "intent_id": intent.get("intent_id"),
        "variant_id": intent.get("variant_id"),
        "asset": intent.get("asset"),
        "side": side,
        "entry_timestamp": intent.get("timestamp"),
        "entry_price": round(entry_price, 8),
        "quantity": quantity,
        "notional_usd": notional,
        "fake_money": True,
        "no_transmit": True,
        "guaranteed_fill": False,
        "fill_type": "conservative_public_forward_fake_fill",
    }
    mark = {
        **fill,
        "mark_id": mark_id,
        "mark_timestamp": future_observation.get("timestamp"),
        "mark_price": round(mark_price, 8),
        "mark_source": "future_public_observation",
        "source_observation_hash": future_observation.get("evidence_hash"),
        "fee_cost": fee_cost,
        "spread_cost": spread_cost,
        "slippage_cost": slippage_cost,
        "net_pnl": net_pnl,
    }
    return fill, mark


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
