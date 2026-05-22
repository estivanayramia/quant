from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_os.research.strategy_factory.campaign_common import (
    load_report,
    safe_payload,
    write_campaign_state,
    write_json_md,
)

KRAKEN_DEPTH_URL = "https://api.kraken.com/0/public/Depth"
KRAKEN_PAIRS = {
    "BTC/USD": "XXBTZUSD",
    "ETH/USD": "XETHZUSD",
    "SOL/USD": "SOLUSD",
    "XRP/USD": "XXRPZUSD",
}
PUBLIC_FORWARD_RETIREMENT_MIN_OBSERVATIONS = 100
PUBLIC_FORWARD_LOW_INTENT_RATE_MIN_OBSERVATIONS = 150
PUBLIC_FORWARD_MIN_INTENT_RATE = 0.01
PUBLIC_FORWARD_LOW_MARK_RATE_MIN_INTENTS = 20
PUBLIC_FORWARD_MIN_MARK_COMPLETION_RATE = 0.05


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
    incoming = [_normalize_observation(row) for row in observations]
    existing_observations = list(previous.get("public_forward_observations") or [])
    if any(not _is_pending_public_forward_observation(row) for row in incoming):
        existing_observations = [
            row for row in existing_observations if not _is_pending_public_forward_observation(row)
        ]
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
    candidate_assets = set(selected_candidate.get("assets") or [])
    history_by_asset: dict[str, list[dict[str, Any]]] = {}
    intents = []
    for index, observation in enumerate(observations):
        asset = str(observation.get("asset") or "")
        if candidate_assets and asset not in candidate_assets:
            continue
        prior_observations = history_by_asset.setdefault(asset, [])
        intent = _build_public_forward_intent(
            index=index,
            candidate=selected_candidate,
            observation=observation,
            prior_observations=prior_observations,
        )
        prior_observations.append(observation)
        if intent:
            intents.append(intent)
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
    resolved_candidate = candidate or _resolve_public_forward_collectable_candidate(output_root)
    observation_summary = append_variant_public_forward_public_snapshot(
        output_root=output_root,
        public_network_ok=public_network_ok,
        public_snapshot=public_snapshot,
        candidate=resolved_candidate,
    )
    intents = write_variant_public_forward_intents_report(
        output_root=output_root,
        candidate=resolved_candidate,
    )
    fills_marks = write_variant_public_forward_fills_and_marks_report(
        output_root=output_root,
        candidate=resolved_candidate,
    )
    from quant_os.proving.thousand_strategy_public_forward_evidence import (
        write_thousand_strategy_public_forward_evidence_report,
    )

    evidence = write_thousand_strategy_public_forward_evidence_report(output_root=output_root)
    write_variant_public_forward_candidate_archive(output_root=output_root)
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


def write_variant_public_forward_batch_cycle(
    *,
    output_root: str | Path = ".",
    cycle_count: int = 1,
    sleep_seconds: float = 0.0,
    public_network_ok: bool = False,
    public_snapshots: Iterable[dict[str, Any]] | None = None,
    candidate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    bounded_cycle_count = max(1, min(int(cycle_count), 50))
    snapshots = list(public_snapshots or [])
    resolved_candidate = candidate or _resolve_public_forward_collectable_candidate(output_root)
    cycle_summaries: list[dict[str, Any]] = []
    latest: dict[str, Any] = {}
    for index in range(bounded_cycle_count):
        snapshot = snapshots[index] if index < len(snapshots) else None
        latest = write_variant_public_forward_collection_cycle(
            output_root=output_root,
            public_network_ok=public_network_ok,
            public_snapshot=snapshot,
            candidate=resolved_candidate,
        )
        cycle_summaries.append(
            {
                "cycle_index": index + 1,
                "selected_strategy_id": latest.get("selected_strategy_id"),
                "observation_count": latest.get("observation_count", 0),
                "eligible_intent_count": latest.get("eligible_intent_count", 0),
                "fake_fill_count": latest.get("fake_fill_count", 0),
                "completed_mark_count": latest.get("completed_mark_count", 0),
                "fake_net_pnl": latest.get("fake_net_pnl", 0.0),
                "public_forward_evidence_status": latest.get("public_forward_evidence_status"),
            }
        )
        if sleep_seconds > 0 and index < bounded_cycle_count - 1:
            time.sleep(min(float(sleep_seconds), 60.0))
    payload = safe_payload(
        status="VARIANT_PUBLIC_FORWARD_BATCH_CYCLE_CHECKPOINTED",
        selected_strategy_id=latest.get("selected_strategy_id"),
        selected_strategy_family=latest.get("selected_strategy_family"),
        selected_strategy_assets=latest.get("selected_strategy_assets", []),
        cycle_count_requested=cycle_count,
        cycle_count_completed=len(cycle_summaries),
        sleep_seconds=min(max(float(sleep_seconds), 0.0), 60.0),
        observation_count=latest.get("observation_count", 0),
        eligible_intent_count=latest.get("eligible_intent_count", 0),
        fake_fill_count=latest.get("fake_fill_count", 0),
        completed_mark_count=latest.get("completed_mark_count", 0),
        fake_net_pnl=latest.get("fake_net_pnl", 0.0),
        public_forward_evidence_status=latest.get("public_forward_evidence_status"),
        public_forward_evidence_proven=False,
        evidence_blockers=latest.get("evidence_blockers", []),
        collection_blockers=latest.get("collection_blockers", []),
        cycle_summaries=cycle_summaries,
        fake_money=True,
        no_transmit=True,
        no_credentials=True,
        no_orders=True,
        next_action="Continue bounded append-only public-forward batch cycles until evidence thresholds are met.",
    )
    return write_json_md(
        payload,
        output_root=output_root,
        report_dir="live_sim",
        json_name="latest_public_forward_batch_cycle.json",
        md_name="latest_public_forward_batch_cycle.md",
        title="Variant Public Forward Batch Cycle",
        lines=[
            f"Status: {payload['status']}",
            f"Selected strategy: {payload['selected_strategy_id']}",
            f"Cycles completed: {payload['cycle_count_completed']}",
            f"Observations: {payload['observation_count']}",
            f"Eligible intents: {payload['eligible_intent_count']}",
            f"Fake fills: {payload['fake_fill_count']}",
            f"Completed marks: {payload['completed_mark_count']}",
            f"Public-forward evidence: {payload['public_forward_evidence_status']}",
            "Bounded, append-only, fake-money, no-transmit public-data collection.",
        ],
    )


def write_variant_public_forward_candidate_archive(
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    previous_archive = load_report(
        output_root=output_root,
        report_dir="live_sim",
        json_name="latest_public_forward_candidate_archive.json",
    )
    live_summary = load_report(
        output_root=output_root,
        report_dir="live_sim",
        json_name="latest_live_sim_summary.json",
    )
    evidence = load_report(
        output_root=output_root,
        report_dir="public_forward_evidence",
        json_name="latest_public_forward_evidence.json",
    )
    candidate_evidence = dict(previous_archive.get("candidate_evidence") or {})
    candidate_id = str(live_summary.get("selected_strategy_id") or "")
    if candidate_id:
        candidate_evidence[candidate_id] = {
            "selected_strategy_id": candidate_id,
            "selected_strategy_family": live_summary.get("selected_strategy_family"),
            "selected_strategy_assets": live_summary.get("selected_strategy_assets", []),
            "observation_count": int(live_summary.get("observation_count") or 0),
            "eligible_intent_count": int(live_summary.get("eligible_intent_count") or 0),
            "fake_fill_count": int(live_summary.get("fake_fill_count") or 0),
            "completed_mark_count": int(live_summary.get("completed_mark_count") or 0),
            "fake_net_pnl": float(live_summary.get("fake_net_pnl") or 0.0),
            "public_forward_evidence_status": evidence.get("status", "PUBLIC_FORWARD_EVIDENCE_BLOCKED"),
            "public_forward_evidence_proven": False,
            "evidence_blockers": evidence.get("blockers", []),
            "data_sources": live_summary.get("data_sources", []),
        }
    payload = safe_payload(
        status="VARIANT_PUBLIC_FORWARD_CANDIDATE_ARCHIVE_READY",
        candidate_count=len(candidate_evidence),
        selected_strategy_id=candidate_id or None,
        candidate_evidence=candidate_evidence,
        public_forward_evidence_proven=False,
        fake_money=True,
        no_transmit=True,
        no_credentials=True,
        no_orders=True,
        next_action="Continue rotating candidates with candidate-scoped public-forward evidence.",
    )
    return write_json_md(
        payload,
        output_root=output_root,
        report_dir="live_sim",
        json_name="latest_public_forward_candidate_archive.json",
        md_name="latest_public_forward_candidate_archive.md",
        title="Variant Public Forward Candidate Archive",
        lines=[
            f"Status: {payload['status']}",
            f"Candidates archived: {payload['candidate_count']}",
            f"Latest selected strategy: {payload['selected_strategy_id']}",
            "Candidate-scoped, fake-money, no-transmit public-forward evidence.",
        ],
    )


def write_variant_public_forward_candidate_rotation(
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    tournament = load_report(
        output_root=output_root,
        report_dir="tournament",
        json_name="latest_tournament.json",
    )
    live_summary = load_report(
        output_root=output_root,
        report_dir="live_sim",
        json_name="latest_live_sim_summary.json",
    )
    archive = load_report(
        output_root=output_root,
        report_dir="live_sim",
        json_name="latest_public_forward_candidate_archive.json",
    )
    current_candidate = dict(tournament.get("current_best_candidate") or {})
    current_candidate_id = str(
        live_summary.get("selected_strategy_id") or current_candidate.get("id") or ""
    )
    retired: dict[str, dict[str, Any]] = {}
    current_reasons = _public_forward_retirement_reasons(live_summary)
    if current_candidate_id and current_reasons:
        retired[current_candidate_id] = {
            "candidate_id": current_candidate_id,
            "family": live_summary.get("selected_strategy_family") or current_candidate.get("family"),
            "assets": live_summary.get("selected_strategy_assets") or current_candidate.get("assets", []),
            "fake_net_pnl": float(live_summary.get("fake_net_pnl") or 0.0),
            "observation_count": int(live_summary.get("observation_count") or 0),
            "completed_mark_count": int(live_summary.get("completed_mark_count") or 0),
            "retirement_reasons": current_reasons,
        }
    for candidate_id, evidence in (archive.get("candidate_evidence") or {}).items():
        reasons = _public_forward_retirement_reasons(evidence)
        if reasons:
            retired[str(candidate_id)] = {
                "candidate_id": str(candidate_id),
                "family": evidence.get("selected_strategy_family"),
                "assets": evidence.get("selected_strategy_assets", []),
                "fake_net_pnl": float(evidence.get("fake_net_pnl") or 0.0),
                "observation_count": int(evidence.get("observation_count") or 0),
                "completed_mark_count": int(evidence.get("completed_mark_count") or 0),
                "retirement_reasons": reasons,
            }

    candidate_groups = [
        _rank_public_forward_rotation_candidates(
            list(tournament.get("cumulative_leaderboard_top_50") or [])
        ),
        _rank_public_forward_rotation_candidates(
            list(tournament.get("public_forward_candidate_pool") or [])
        ),
        _rank_public_forward_rotation_candidates(list(tournament.get("leaderboard_top_50") or [])),
        _rank_public_forward_rotation_candidates(list(tournament.get("top_candidates") or [])),
    ]
    seen_candidate_ids: set[str] = set()
    skipped_uncollectable: list[str] = []
    selected: dict[str, Any] | None = None
    for group in candidate_groups:
        group_candidates = [
            candidate
            for candidate in group
            if str(candidate.get("id") or "")
            and str(candidate.get("id") or "") not in seen_candidate_ids
        ]
        group_skipped = [
            str(candidate.get("id"))
            for candidate in group_candidates
            if str(candidate.get("id") or "") not in retired
            and not _is_public_forward_collectable_candidate(candidate)
        ]
        for candidate in group_candidates:
            candidate_id = str(candidate.get("id") or "")
            seen_candidate_ids.add(candidate_id)
            if candidate_id in retired:
                continue
            if not _is_public_forward_collectable_candidate(candidate):
                continue
            selected = dict(candidate)
            skipped_uncollectable = group_skipped
            break
        if selected is not None:
            break
    blockers: list[str] = []
    if not retired:
        blockers.append("NO_PUBLIC_FORWARD_RETIREMENT_TRIGGER")
    if selected is None:
        blockers.append("NO_ROTATION_CANDIDATE_AVAILABLE")

    status = (
        "VARIANT_PUBLIC_FORWARD_CANDIDATE_ROTATED"
        if retired and selected is not None
        else "VARIANT_PUBLIC_FORWARD_CANDIDATE_ROTATION_BLOCKED"
    )
    if selected is not None and retired:
        tournament = dict(tournament)
        tournament["public_forward_retired_candidates"] = list(retired.values())
        tournament["current_best_candidate"] = selected
        tournament["best_fake_pnl"] = selected.get("fake_net_pnl", 0.0)
        tournament["baseline_beaten"] = bool(selected.get("baseline_beaten"))
        tournament["placebo_beaten"] = bool(selected.get("placebo_beaten"))
        write_json_md(
            tournament,
            output_root=output_root,
            report_dir="tournament",
            json_name="latest_tournament.json",
            md_name="latest_tournament.md",
            title="Strategy Tournament",
            lines=[
                f"Status: {tournament.get('status')}",
                f"Current best candidate: {selected.get('id')}",
                "Public-forward negative-PnL candidate retired for rotation.",
                "Campaign complete: False",
            ],
        )
        write_campaign_state(
            output_root=output_root,
            current_best_candidate=selected,
            public_forward_retired_candidates=list(retired.values()),
            blockers=[
                "PUBLIC_FORWARD_EVIDENCE_NOT_PROVEN",
                "OVERFIT_GUARD_NOT_PASSED",
                "REPEATABILITY_NOT_PASSED",
            ],
            next_action="Collect public-forward evidence for the rotated candidate.",
        )
        write_variant_public_forward_live_sim_summary(output_root=output_root, candidate=selected)

    retired_values = list(retired.values())
    payload = safe_payload(
        status=status,
        blockers=blockers,
        retired_candidate_id=retired_values[0]["candidate_id"] if retired_values else None,
        retirement_reasons=retired_values[0]["retirement_reasons"] if retired_values else [],
        retired_candidates=retired_values,
        skipped_uncollectable_candidate_ids=skipped_uncollectable,
        selected_strategy_id=selected.get("id") if selected else None,
        selected_strategy_family=selected.get("family") if selected else None,
        selected_strategy_assets=selected.get("assets", []) if selected else [],
        public_forward_evidence_proven=False,
        fake_money=True,
        no_transmit=True,
        no_credentials=True,
        no_orders=True,
        next_action=(
            "Collect public-forward observations for rotated candidate."
            if status == "VARIANT_PUBLIC_FORWARD_CANDIDATE_ROTATED"
            else "Continue current candidate or generate more tournament candidates."
        ),
    )
    return write_json_md(
        payload,
        output_root=output_root,
        report_dir="live_sim",
        json_name="latest_public_forward_candidate_rotation.json",
        md_name="latest_public_forward_candidate_rotation.md",
        title="Variant Public Forward Candidate Rotation",
        lines=[
            f"Status: {payload['status']}",
            f"Retired candidate: {payload['retired_candidate_id']}",
            f"Selected strategy: {payload['selected_strategy_id']}",
            f"Blockers: {', '.join(blockers) if blockers else 'None'}",
            "Fake-money, no-transmit rotation only.",
        ],
    )


def write_variant_public_forward_proof_finalizer(
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    live_summary = load_report(
        output_root=output_root,
        report_dir="live_sim",
        json_name="latest_live_sim_summary.json",
    )
    fills_marks = load_report(
        output_root=output_root,
        report_dir="live_sim",
        json_name="latest_public_forward_fills_and_marks.json",
    )
    data_sources = [str(source) for source in live_summary.get("data_sources", [])]
    observation_count = int(live_summary.get("observation_count") or 0)
    eligible_intent_count = int(live_summary.get("eligible_intent_count") or 0)
    fake_fill_count = int(live_summary.get("fake_fill_count") or 0)
    completed_mark_count = int(live_summary.get("completed_mark_count") or 0)
    fake_net_pnl = float(live_summary.get("fake_net_pnl") or 0.0)
    blockers: list[str] = []
    if not live_summary.get("selected_strategy_id"):
        blockers.append("NO_SELECTED_CANDIDATE")
    if not data_sources:
        blockers.append("PUBLIC_FORWARD_DATA_SOURCE_MISSING")
    if any("fixture" in source.lower() for source in data_sources):
        blockers.append("FIXTURE_DATA_NOT_PUBLIC_FORWARD_EVIDENCE")
    if any("pending" in source.lower() for source in data_sources):
        blockers.append("PUBLIC_FORWARD_DATA_SOURCE_PENDING")
    if observation_count < 1000:
        blockers.append("PUBLIC_FORWARD_OBSERVATION_COUNT_TOO_LOW")
    if eligible_intent_count < 300:
        blockers.append("PUBLIC_FORWARD_INTENT_COUNT_TOO_LOW")
    if fake_fill_count < 150:
        blockers.append("PUBLIC_FORWARD_FAKE_FILL_COUNT_TOO_LOW")
    if completed_mark_count < 150:
        blockers.append("PUBLIC_FORWARD_COMPLETED_MARK_COUNT_TOO_LOW")
    if fake_net_pnl <= 0:
        blockers.append("PUBLIC_FORWARD_FAKE_NET_PNL_NOT_POSITIVE")
    if fills_marks.get("lookahead_detected") is True:
        blockers.append("PUBLIC_FORWARD_LOOKAHEAD_DETECTED")

    ready = not blockers
    if ready:
        ready_summary = dict(live_summary)
        ready_summary.update(
            status="VARIANT_LIVE_SIM_SUMMARY_READY",
            evidence_source="public_forward_live_sim",
            public_forward_evidence_proven=True,
        )
        write_json_md(
            ready_summary,
            output_root=output_root,
            report_dir="live_sim",
            json_name="latest_live_sim_summary.json",
            md_name="latest_live_sim_summary.md",
            title="Variant Public Forward Live Sim Summary",
            lines=[
                "Status: VARIANT_LIVE_SIM_SUMMARY_READY",
                f"Selected strategy: {ready_summary.get('selected_strategy_id')}",
                f"Observations: {ready_summary.get('observation_count')}",
                f"Eligible intents: {ready_summary.get('eligible_intent_count')}",
                f"Fake fills: {ready_summary.get('fake_fill_count')}",
                f"Completed marks: {ready_summary.get('completed_mark_count')}",
                f"Fake net PnL: {ready_summary.get('fake_net_pnl')}",
                "Public-forward evidence source is proven without live orders, auth, credentials, or signing.",
            ],
        )
        reconciliation = safe_payload(
            status="VARIANT_LIVE_SIM_RECONCILIATION_PASSED",
            selected_strategy_id=ready_summary.get("selected_strategy_id"),
            observation_count=observation_count,
            eligible_intent_count=eligible_intent_count,
            fake_fill_count=fake_fill_count,
            completed_mark_count=completed_mark_count,
            fake_net_pnl=round(fake_net_pnl, 8),
            public_forward_evidence_proven=True,
            no_credentials=True,
            no_orders=True,
        )
        write_json_md(
            reconciliation,
            output_root=output_root,
            report_dir="live_sim",
            json_name="latest_reconciliation.json",
            md_name="latest_reconciliation.md",
            title="Variant Public Forward Reconciliation",
            lines=[
                f"Status: {reconciliation['status']}",
                f"Selected strategy: {reconciliation['selected_strategy_id']}",
                "No live orders, auth, credentials, or signing.",
            ],
        )

    payload = safe_payload(
        status="VARIANT_PUBLIC_FORWARD_PROOF_READY" if ready else "VARIANT_PUBLIC_FORWARD_PROOF_BLOCKED",
        blockers=blockers,
        selected_strategy_id=live_summary.get("selected_strategy_id"),
        observation_count=observation_count,
        eligible_intent_count=eligible_intent_count,
        fake_fill_count=fake_fill_count,
        completed_mark_count=completed_mark_count,
        fake_net_pnl=round(fake_net_pnl, 8),
        data_sources=data_sources,
        public_forward_evidence_proven=ready,
        evidence_source="public_forward_live_sim" if ready else "public_forward_live_sim_pending",
        fake_money=True,
        no_transmit=True,
        no_credentials=True,
        no_orders=True,
        next_action=(
            "Run public-forward evidence, overfit, repeatability, capacity, and readiness gates."
            if ready
            else "Continue public-forward accumulation until strict proof thresholds are met."
        ),
    )
    write_variant_public_forward_candidate_archive(output_root=output_root)
    return write_json_md(
        payload,
        output_root=output_root,
        report_dir="live_sim",
        json_name="latest_public_forward_proof_finalizer.json",
        md_name="latest_public_forward_proof_finalizer.md",
        title="Variant Public Forward Proof Finalizer",
        lines=[
            f"Status: {payload['status']}",
            f"Selected strategy: {payload['selected_strategy_id']}",
            f"Blockers: {', '.join(blockers) if blockers else 'None'}",
            f"Fake net PnL: {payload['fake_net_pnl']}",
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


def _is_pending_public_forward_observation(row: dict[str, Any]) -> bool:
    source = str(row.get("source") or "").lower()
    timestamp = str(row.get("timestamp") or "").lower()
    return "pending" in source or timestamp == "pending"


def _public_forward_retirement_reasons(report: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    observations = int(report.get("observation_count") or 0)
    eligible_intents = int(report.get("eligible_intent_count") or 0)
    completed_marks = int(report.get("completed_mark_count") or 0)
    fake_net_pnl = float(report.get("fake_net_pnl") or 0.0)
    if completed_marks > 0 and fake_net_pnl < 0:
        reasons.append("PUBLIC_FORWARD_FAKE_NET_PNL_NEGATIVE")
    if observations >= PUBLIC_FORWARD_RETIREMENT_MIN_OBSERVATIONS and eligible_intents == 0:
        reasons.append("PUBLIC_FORWARD_NO_SIGNAL_AFTER_MIN_OBSERVATIONS")
    if observations >= PUBLIC_FORWARD_LOW_INTENT_RATE_MIN_OBSERVATIONS and eligible_intents > 0:
        intent_rate = eligible_intents / observations
        if intent_rate < PUBLIC_FORWARD_MIN_INTENT_RATE:
            reasons.append("PUBLIC_FORWARD_INTENT_RATE_TOO_LOW")
    if eligible_intents >= PUBLIC_FORWARD_LOW_MARK_RATE_MIN_INTENTS:
        mark_completion_rate = completed_marks / eligible_intents
        if mark_completion_rate < PUBLIC_FORWARD_MIN_MARK_COMPLETION_RATE:
            reasons.append("PUBLIC_FORWARD_MARK_COMPLETION_RATE_TOO_LOW")
    return reasons


def _resolve_public_forward_collectable_candidate(output_root: str | Path) -> dict[str, Any] | None:
    tournament = load_report(
        output_root=output_root,
        report_dir="tournament",
        json_name="latest_tournament.json",
    )
    current = dict(tournament.get("current_best_candidate") or {})
    if _is_public_forward_collectable_candidate(current):
        return current

    live_summary = load_report(
        output_root=output_root,
        report_dir="live_sim",
        json_name="latest_live_sim_summary.json",
    )
    selected_id = str(live_summary.get("selected_strategy_id") or "")
    if selected_id:
        selected = _candidate_from_tournament(tournament, selected_id)
        if selected and _is_public_forward_collectable_candidate(selected):
            return selected
        summary_candidate = {
            "id": selected_id,
            "family": live_summary.get("selected_strategy_family"),
            "assets": live_summary.get("selected_strategy_assets", []),
        }
        if _is_public_forward_collectable_candidate(summary_candidate):
            return summary_candidate

    for candidate in (
        _dedup_public_forward_candidates(
            [
                *(tournament.get("cumulative_leaderboard_top_50") or []),
                *(tournament.get("public_forward_candidate_pool") or []),
                *(tournament.get("leaderboard_top_50") or []),
                *(tournament.get("top_candidates") or []),
            ]
        )
    ):
        if _is_public_forward_collectable_candidate(candidate):
            return dict(candidate)
    return current or None


def _candidate_from_tournament(
    tournament: dict[str, Any],
    candidate_id: str,
) -> dict[str, Any] | None:
    candidates = [
        tournament.get("current_best_candidate"),
        tournament.get("latest_batch_best_candidate"),
        *(tournament.get("cumulative_leaderboard_top_50") or []),
        *(tournament.get("public_forward_candidate_pool") or []),
        *(tournament.get("leaderboard_top_50") or []),
        *(tournament.get("top_candidates") or []),
    ]
    for candidate in candidates:
        if isinstance(candidate, dict) and str(candidate.get("id")) == candidate_id:
            return dict(candidate)
    return None


def _dedup_public_forward_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in candidates:
        candidate_id = str(candidate.get("id") or "")
        if not candidate_id or candidate_id in seen:
            continue
        seen.add(candidate_id)
        deduped.append(candidate)
    return deduped


def _rank_public_forward_rotation_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(candidates, key=_public_forward_rotation_priority, reverse=True)


def _public_forward_rotation_priority(candidate: dict[str, Any]) -> tuple[int, int, int, float, float]:
    eligible_intents = int(candidate.get("eligible_intents") or 0)
    completed_marks = int(candidate.get("completed_marks") or 0)
    fake_net_pnl = float(candidate.get("fake_net_pnl") or 0.0)
    score = float(candidate.get("score") or 0.0)
    crypto_collectable = 1 if _is_public_forward_collectable_candidate(candidate) else 0
    historically_executable = 1 if eligible_intents >= 300 and completed_marks >= 150 else 0
    return (
        crypto_collectable,
        historically_executable,
        eligible_intents,
        fake_net_pnl,
        score,
    )


def _is_public_forward_collectable_candidate(candidate: dict[str, Any]) -> bool:
    return (
        any(str(asset) in KRAKEN_PAIRS for asset in candidate.get("assets", []) or [])
        and _public_forward_family_signal_mode(candidate) is not None
    )


def _build_public_forward_intent(
    *,
    index: int,
    candidate: dict[str, Any],
    observation: dict[str, Any],
    prior_observations: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    signal = _public_forward_signal(
        candidate=candidate,
        observation=observation,
        prior_observations=prior_observations or [],
    )
    if signal is None:
        return None
    side = signal["side"]
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
        **signal,
    }
    payload["intent_id"] = _stable_hash({"intent": payload, "index": index}).replace(
        "pfobs_",
        "pfint_",
        1,
    )
    return payload


def _public_forward_signal(
    *,
    candidate: dict[str, Any],
    observation: dict[str, Any],
    prior_observations: list[dict[str, Any]],
) -> dict[str, Any] | None:
    lookback_observations = _public_forward_signal_lookback_observations(candidate)
    if len(prior_observations) < lookback_observations:
        return None
    previous_observation = prior_observations[-lookback_observations]
    current_mid = _public_forward_mid_price(observation)
    previous_mid = _public_forward_mid_price(previous_observation)
    if current_mid <= 0.0 or previous_mid <= 0.0:
        return None
    change_bps = ((current_mid - previous_mid) / previous_mid) * 10_000.0
    execution_uncertainty_bps = _public_forward_execution_uncertainty_bps(observation)
    threshold_bps = max(
        _public_forward_signal_threshold_bps(candidate),
        execution_uncertainty_bps,
    )
    if abs(change_bps) < threshold_bps:
        return None

    signal_mode = _public_forward_family_signal_mode(candidate)
    if signal_mode is None:
        return None

    follows_move = signal_mode == "momentum"
    up_move = change_bps > 0.0
    side = "buy" if up_move == follows_move else "sell"
    direction_suffix = "up" if up_move else "down"
    return {
        "side": side,
        "signal_direction": f"{signal_mode}_{direction_suffix}",
        "signal_reason": "candidate_family_mid_price_change_threshold",
        "signal_change_bps": round(change_bps, 6),
        "signal_threshold_bps": round(threshold_bps, 6),
        "signal_lookback_observations": lookback_observations,
        "execution_uncertainty_bps": round(execution_uncertainty_bps, 6),
        "execution_uncertainty_reason": "fee_spread_slippage_and_observed_spread",
        "candidate_signal_model": "public_forward_no_lookahead_mid_change",
        "uses_lookahead": False,
    }


def _public_forward_family_signal_mode(candidate: dict[str, Any]) -> str | None:
    family = str(candidate.get("family") or "").lower()
    if any(token in family for token in ("reversion", "reversal", "snapback", "failure")):
        return "reversion"
    if any(
        token in family
        for token in (
            "momentum",
            "trend",
            "breakout",
            "continuation",
            "relative_strength",
            "source_quality",
            "quality_filtered",
            "no_trade_veto",
            "moving_average",
        )
    ):
        return "momentum"
    return None


def _public_forward_mid_price(observation: dict[str, Any]) -> float:
    bid = float(observation.get("bid") or 0.0)
    ask = float(observation.get("ask") or 0.0)
    if bid <= 0.0 or ask <= 0.0:
        return 0.0
    return (bid + ask) / 2.0


def _public_forward_execution_uncertainty_bps(observation: dict[str, Any]) -> float:
    mid = _public_forward_mid_price(observation)
    if mid <= 0.0:
        return 20.0
    bid = float(observation.get("bid") or 0.0)
    ask = float(observation.get("ask") or 0.0)
    observed_spread_bps = ((ask - bid) / mid) * 10_000.0 if ask > bid > 0.0 else 0.0
    modeled_fee_spread_slippage_bps = 20.0
    return modeled_fee_spread_slippage_bps + max(0.0, observed_spread_bps)


def _public_forward_signal_threshold_bps(candidate: dict[str, Any]) -> float:
    thresholds = (
        candidate.get("variant_configuration", {}).get("thresholds", {})
        or candidate.get("thresholds", {})
        or {}
    )
    return max(0.0, float(thresholds.get("no_trade_edge_bps") or 1.0))


def _public_forward_signal_lookback_observations(candidate: dict[str, Any]) -> int:
    variant_configuration = candidate.get("variant_configuration", {}) or {}
    configured = variant_configuration.get("lookback", candidate.get("lookback", 1))
    return max(1, min(60, int(configured or 1)))


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
