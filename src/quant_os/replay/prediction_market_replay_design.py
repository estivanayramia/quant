from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.replay.prediction_market_replay_inputs import (
    build_replay_input_summary,
    normalize_replay_inputs,
)

REPORT_ROOT = Path("reports/sequence31/replay_design")
REPLAY_DESIGN_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
    "prediction_market_execution_authority_added": False,
}


def write_replay_design_report(
    *,
    output_root: str | Path = ".",
    polymarket_snapshot_path: str | Path | None = None,
    pmxt_manifest_path: str | Path | None = None,
    reference_datasets_manifest_path: str | Path | None = None,
) -> dict[str, Any]:
    payload = build_replay_design(
        polymarket_snapshot_path=polymarket_snapshot_path,
        pmxt_manifest_path=pmxt_manifest_path,
        reference_datasets_manifest_path=reference_datasets_manifest_path,
    )
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def build_replay_design(
    *,
    polymarket_snapshot_path: str | Path | None = None,
    pmxt_manifest_path: str | Path | None = None,
    reference_datasets_manifest_path: str | Path | None = None,
) -> dict[str, Any]:
    events = normalize_replay_inputs(
        polymarket_snapshot_path=polymarket_snapshot_path,
        pmxt_manifest_path=pmxt_manifest_path,
        reference_datasets_manifest_path=reference_datasets_manifest_path,
    )
    summary = build_replay_input_summary(events)
    timeline = [_timeline_entry(index, event.to_report_dict()) for index, event in enumerate(events)]
    blockers = _design_blockers(summary)
    status = "REPLAY_DESIGN_PARTIAL" if timeline else "REPLAY_INPUTS_TOO_THIN"
    return {
        "sequence": "31",
        "selected_lane_id": "prediction_market_replay_input_infrastructure",
        "replay_design_status": status,
        "blockers": blockers,
        "event_ordering_rules": [
            "Sort by event timestamp when present.",
            "Use event_type/source/market/token/snapshot stable tie-breakers.",
            "Treat events without timestamps as known only at manifest inspection time.",
            "Never let later events influence earlier shadow decisions.",
        ],
        "market_state_transition_rules": [
            "market_state updates metadata and token context.",
            "orderbook_snapshot replaces visible best bid/ask state for its token.",
            "trade records observed prints but does not prove queue position or fill priority.",
            "archive manifests record possible future data availability only.",
        ],
        "known_at_event_time": [
            "event_type",
            "source_id",
            "provenance",
            "timestamp when supplied",
            "market_id or condition_id when supplied",
            "token_id/outcome when supplied",
            "visible top-of-book prices and sizes when supplied",
            "trade price/size when supplied",
        ],
        "unknowns": [
            "full depth beyond supplied levels",
            "queue position",
            "fill priority",
            "hidden liquidity",
            "venue latency distribution",
            "perfect market lifecycle and resolution timing",
        ],
        "venue_limitations": [
            "partial_book_depth",
            "no_guaranteed_queue_position",
            "uncertain_fill_priority",
            "latency_uncertainty",
            "missing_hidden_liquidity",
            "imperfect_lifecycle_resolution_timing",
        ],
        "event_timeline": timeline,
        "replay_input_summary": {
            "event_count": summary["event_count"],
            "event_counts": summary["event_counts"],
            "quality_flag_counts": summary["quality_flag_counts"],
        },
        **REPLAY_DESIGN_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _timeline_entry(index: int, event: dict[str, Any]) -> dict[str, Any]:
    known_fields = [
        key
        for key, value in event.items()
        if value not in (None, [], {}) and key not in {"quality_flags"}
    ]
    unknown_fields = [
        "queue_position",
        "fill_priority",
        "hidden_liquidity",
        "latency",
    ]
    if event["timestamp"] is None:
        unknown_fields.append("event_time")
    return {
        "event_index": index,
        "event_type": event["event_type"],
        "source_id": event["source_id"],
        "timestamp": event["timestamp"],
        "market_id": event["market_id"],
        "condition_id": event["condition_id"],
        "slug": event["slug"],
        "token_id": event["token_id"],
        "known_fields": known_fields,
        "unknown_fields": unknown_fields,
        "quality_flags": event["quality_flags"],
        "state_transition": _state_transition(event["event_type"]),
        "raw_event": event,
    }


def _state_transition(event_type: str) -> str:
    if event_type == "market_state":
        return "update_market_metadata"
    if event_type == "orderbook_snapshot":
        return "replace_visible_top_of_book"
    if event_type == "trade":
        return "record_observed_trade"
    if event_type.endswith("_archive_manifest"):
        return "record_archive_availability"
    return "record_reference_context"


def _design_blockers(summary: dict[str, Any]) -> list[str]:
    blockers = []
    event_counts = summary["event_counts"]
    if event_counts.get("orderbook_snapshot", 0) < 10:
        blockers.append("ORDERBOOK_HISTORY_TOO_THIN")
    if event_counts.get("trade", 0) < 10:
        blockers.append("TRADE_HISTORY_TOO_THIN")
    if summary["quality_flag_counts"]:
        blockers.append("QUALITY_FLAGS_PRESENT")
    blockers.append("REPLAY_LIMITATIONS_UNMODELED")
    return blockers


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_replay_design.json"
    md_path = root / "latest_replay_design.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 31 Replay Design",
        "",
        "Deterministic replay design for prediction-market replay inputs. No execution authority.",
        "",
        f"Status: {payload['replay_design_status']}",
        f"Selected lane: {payload['selected_lane_id']}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Event Ordering Rules",
    ]
    lines.extend(f"- {item}" for item in payload["event_ordering_rules"])
    lines.extend(["", "## Venue Limitations"])
    lines.extend(f"- {item}" for item in payload["venue_limitations"])
    lines.extend(["", "## Blockers"])
    lines.extend(f"- {item}" for item in payload["blockers"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
