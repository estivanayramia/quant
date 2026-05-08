from __future__ import annotations

import json
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from quant_os.replay.prediction_market_event_schema import (
    PredictionMarketReplayEvent,
    normalize_decimal,
)

REPORT_ROOT = Path("reports/sequence28/replay_inputs")
SCHEMA_VERSION = "prediction_market_replay_inputs_v1"
REPLAY_INPUT_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
    "prediction_market_execution_authority_added": False,
}


def normalize_replay_inputs(
    *,
    polymarket_snapshot_path: str | Path | None = None,
    pmxt_manifest_path: str | Path | None = None,
    reference_datasets_manifest_path: str | Path | None = None,
) -> list[PredictionMarketReplayEvent]:
    events: list[PredictionMarketReplayEvent] = []
    if polymarket_snapshot_path is not None:
        events.extend(_normalize_polymarket_snapshot(Path(polymarket_snapshot_path)))
    if pmxt_manifest_path is not None:
        events.extend(_normalize_pmxt_manifest(Path(pmxt_manifest_path)))
    if reference_datasets_manifest_path is not None:
        events.extend(_normalize_reference_dataset_manifest(Path(reference_datasets_manifest_path)))
    return sorted(events, key=_sort_key)


def write_replay_input_summary(
    *,
    output_root: str | Path = ".",
    polymarket_snapshot_path: str | Path | None = None,
    pmxt_manifest_path: str | Path | None = None,
    reference_datasets_manifest_path: str | Path | None = None,
) -> dict[str, Any]:
    events = normalize_replay_inputs(
        polymarket_snapshot_path=polymarket_snapshot_path,
        pmxt_manifest_path=pmxt_manifest_path,
        reference_datasets_manifest_path=reference_datasets_manifest_path,
    )
    payload = build_replay_input_summary(events)
    payload["input_paths"] = {
        "polymarket_snapshot_path": _string_path(polymarket_snapshot_path),
        "pmxt_manifest_path": _string_path(pmxt_manifest_path),
        "reference_datasets_manifest_path": _string_path(reference_datasets_manifest_path),
    }
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def build_replay_input_summary(events: list[PredictionMarketReplayEvent]) -> dict[str, Any]:
    event_counts = Counter(event.event_type for event in events)
    quality_counts = Counter(flag for event in events for flag in event.quality_flags)
    source_counts = Counter(event.source_id for event in events)
    market_ids = sorted({event.market_id for event in events if event.market_id})
    token_ids = sorted({event.token_id for event in events if event.token_id})
    status = "PASS" if events else "FAIL"
    return {
        "schema_version": SCHEMA_VERSION,
        "sequence": "28",
        "status": status,
        "event_count": len(events),
        "event_counts": dict(sorted(event_counts.items())),
        "source_counts": dict(sorted(source_counts.items())),
        "market_count": len(market_ids),
        "token_count": len(token_ids),
        "quality_flag_counts": dict(sorted(quality_counts.items())),
        "events": [event.to_report_dict() for event in events],
        "limitations": [
            "Normalized records are replay input candidates only, not an execution model.",
            "Queue position, partial fills, fees, latency, and adverse selection remain unmodeled.",
            "Archive manifests prove candidate data availability, not record-level replay completeness.",
        ],
        **REPLAY_INPUT_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _normalize_polymarket_snapshot(path: Path) -> list[PredictionMarketReplayEvent]:
    payload = _read_json(path)
    provenance = f"local_fixture:{path.name}:polymarket_public_snapshot"
    snapshot_id = path.stem
    markets = payload.get("markets", [])
    market_lookup = _build_market_lookup(markets)
    events: list[PredictionMarketReplayEvent] = []
    for market in markets:
        context = _market_context_from_market(market)
        tokens = market.get("tokens") or []
        base_flags = _base_market_flags(context, timestamp=market.get("timestamp"))
        if not tokens:
            events.append(
                PredictionMarketReplayEvent(
                    event_type="market_state",
                    source_id="py_clob_client_public",
                    provenance=provenance,
                    timestamp=market.get("timestamp"),
                    market_id=context["market_id"],
                    condition_id=context["condition_id"],
                    slug=context["slug"],
                    snapshot_id=snapshot_id,
                    quality_flags=_dedupe((*base_flags, "missing_tokens")),
                )
            )
        for token in tokens:
            token_id = token.get("token_id")
            flags = list(base_flags)
            if not token_id:
                flags.append("missing_token_id")
            events.append(
                PredictionMarketReplayEvent(
                    event_type="market_state",
                    source_id="py_clob_client_public",
                    provenance=provenance,
                    timestamp=market.get("timestamp"),
                    market_id=context["market_id"],
                    condition_id=context["condition_id"],
                    slug=context["slug"],
                    token_id=token_id,
                    outcome=token.get("outcome"),
                    snapshot_id=snapshot_id,
                    quality_flags=_dedupe(flags),
                )
            )
    for orderbook in payload.get("orderbooks", []):
        events.append(
            _normalize_orderbook(
                orderbook,
                market_lookup=market_lookup,
                provenance=provenance,
                snapshot_id=snapshot_id,
            )
        )
    for trade in payload.get("trades", []):
        events.append(
            _normalize_trade(
                trade,
                market_lookup=market_lookup,
                provenance=provenance,
                snapshot_id=snapshot_id,
            )
        )
    return events


def _normalize_orderbook(
    orderbook: dict[str, Any],
    *,
    market_lookup: dict[str, dict[str, Any]],
    provenance: str,
    snapshot_id: str,
) -> PredictionMarketReplayEvent:
    context = _lookup_market_context(orderbook, market_lookup)
    bids = orderbook.get("bids") or []
    asks = orderbook.get("asks") or []
    best_bid = _best_quote(bids, side="bid")
    best_ask = _best_quote(asks, side="ask")
    flags = _base_market_flags(context, timestamp=orderbook.get("timestamp"))
    if not bids or not asks:
        flags.append("empty_orderbook_side")
    if not orderbook.get("token_id"):
        flags.append("missing_token_id")
    return PredictionMarketReplayEvent(
        event_type="orderbook_snapshot",
        source_id="py_clob_client_public",
        provenance=provenance,
        timestamp=orderbook.get("timestamp"),
        market_id=context["market_id"],
        condition_id=context["condition_id"],
        slug=context["slug"],
        token_id=orderbook.get("token_id"),
        outcome=_token_outcome(context, orderbook.get("token_id")),
        best_bid_price=normalize_decimal(best_bid.get("price")) if best_bid else None,
        best_bid_size=normalize_decimal(best_bid.get("size")) if best_bid else None,
        best_ask_price=normalize_decimal(best_ask.get("price")) if best_ask else None,
        best_ask_size=normalize_decimal(best_ask.get("size")) if best_ask else None,
        snapshot_id=snapshot_id,
        quality_flags=_dedupe(flags),
        raw_metadata={"bid_levels": len(bids), "ask_levels": len(asks)},
    )


def _normalize_trade(
    trade: dict[str, Any],
    *,
    market_lookup: dict[str, dict[str, Any]],
    provenance: str,
    snapshot_id: str,
) -> PredictionMarketReplayEvent:
    context = _lookup_market_context(trade, market_lookup)
    flags = _base_market_flags(context, timestamp=trade.get("timestamp"))
    if trade.get("price") is None:
        flags.append("missing_trade_price")
    if trade.get("size") is None:
        flags.append("missing_trade_size")
    if not trade.get("token_id"):
        flags.append("missing_token_id")
    return PredictionMarketReplayEvent(
        event_type="trade",
        source_id="py_clob_client_public",
        provenance=provenance,
        timestamp=trade.get("timestamp"),
        market_id=context["market_id"],
        condition_id=context["condition_id"],
        slug=context["slug"],
        token_id=trade.get("token_id"),
        outcome=_token_outcome(context, trade.get("token_id")),
        trade_price=normalize_decimal(trade.get("price")),
        trade_size=normalize_decimal(trade.get("size")),
        snapshot_id=snapshot_id,
        quality_flags=_dedupe(flags),
    )


def _normalize_pmxt_manifest(path: Path) -> list[PredictionMarketReplayEvent]:
    payload = _read_json(path)
    provenance = f"local_manifest:{path.name}:pmxt"
    snapshot_id = str(payload.get("snapshot_date") or path.stem)
    events = []
    for file_record in payload.get("files", []):
        kind = file_record.get("kind") or "unknown"
        event_type = f"{kind}_archive_manifest"
        flags = _manifest_quality_flags(file_record)
        events.append(
            PredictionMarketReplayEvent(
                event_type=event_type,
                source_id="pmxt_orderbook_archives",
                provenance=provenance,
                timestamp=payload.get("snapshot_date"),
                snapshot_id=snapshot_id,
                quality_flags=_dedupe(flags),
                raw_metadata={
                    "path": file_record.get("path"),
                    "rows": file_record.get("rows"),
                    "columns": file_record.get("columns") or [],
                },
            )
        )
    return events


def _normalize_reference_dataset_manifest(path: Path) -> list[PredictionMarketReplayEvent]:
    payload = _read_json(path)
    provenance = f"local_manifest:{path.name}:reference_datasets"
    events = []
    for dataset in payload.get("datasets", []):
        flags = []
        if not dataset.get("source_id"):
            flags.append("missing_source_id")
        if not dataset.get("rows"):
            flags.append("missing_or_empty_rows")
        if not dataset.get("files"):
            flags.append("missing_files")
        events.append(
            PredictionMarketReplayEvent(
                event_type="reference_dataset_manifest",
                source_id=dataset.get("source_id") or "reference_dataset_unknown",
                provenance=provenance,
                snapshot_id=dataset.get("name"),
                quality_flags=_dedupe(flags),
                raw_metadata={
                    "format": dataset.get("format"),
                    "rows": dataset.get("rows"),
                    "size_gb": dataset.get("size_gb"),
                    "files": dataset.get("files") or [],
                },
            )
        )
    return events


def _build_market_lookup(markets: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for market in markets:
        context = _market_context_from_market(market)
        for key in (context["slug"], context["condition_id"], context["market_id"]):
            if key:
                lookup[str(key)] = context
    return lookup


def _market_context_from_market(market: dict[str, Any]) -> dict[str, Any]:
    slug = market.get("market_slug") or market.get("slug") or market.get("market")
    condition_id = market.get("condition_id")
    market_id = market.get("market_id") or condition_id or slug
    tokens = {
        token.get("token_id"): token.get("outcome")
        for token in market.get("tokens", [])
        if token.get("token_id")
    }
    return {
        "market_id": market_id,
        "condition_id": condition_id,
        "slug": slug,
        "tokens": tokens,
    }


def _lookup_market_context(
    record: dict[str, Any],
    market_lookup: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    market_ref = (
        record.get("market")
        or record.get("market_id")
        or record.get("condition_id")
        or record.get("market_slug")
        or record.get("slug")
    )
    context = market_lookup.get(str(market_ref)) if market_ref is not None else None
    if context is not None:
        return context
    return {
        "market_id": record.get("market_id") or record.get("condition_id") or market_ref,
        "condition_id": record.get("condition_id"),
        "slug": record.get("market_slug") or record.get("slug") or record.get("market"),
        "tokens": {},
    }


def _base_market_flags(context: dict[str, Any], *, timestamp: Any) -> list[str]:
    flags = []
    if timestamp is None:
        flags.append("missing_timestamp")
    if not context.get("market_id"):
        flags.append("missing_market_id")
    if not context.get("condition_id"):
        flags.append("missing_condition_id")
    if not context.get("slug"):
        flags.append("missing_slug")
    return flags


def _token_outcome(context: dict[str, Any], token_id: Any) -> str | None:
    if token_id is None:
        return None
    return context.get("tokens", {}).get(token_id)


def _best_quote(quotes: list[dict[str, Any]], *, side: str) -> dict[str, Any] | None:
    valid_quotes = [quote for quote in quotes if quote.get("price") is not None]
    if not valid_quotes:
        return None
    reverse = side == "bid"
    return sorted(valid_quotes, key=lambda quote: _decimal_sort_value(quote["price"]), reverse=reverse)[0]


def _decimal_sort_value(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _manifest_quality_flags(file_record: dict[str, Any]) -> list[str]:
    flags = []
    columns = set(file_record.get("columns") or [])
    kind = file_record.get("kind")
    if not file_record.get("path"):
        flags.append("missing_path")
    if not file_record.get("rows"):
        flags.append("missing_or_empty_rows")
    if kind == "orderbook":
        required = {"market_id", "token_id", "timestamp", "bid_price", "ask_price"}
        if not required <= columns:
            flags.append("missing_orderbook_columns")
    if kind == "market" and "market_id" not in columns:
        flags.append("missing_market_id_column")
    return flags


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _dedupe(items: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    seen = set()
    deduped = []
    for item in items:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return tuple(deduped)


def _sort_key(event: PredictionMarketReplayEvent) -> tuple[str, str, str, str, str, str]:
    return (
        event.timestamp or "",
        event.event_type,
        event.source_id,
        event.slug or event.market_id or "",
        event.token_id or "",
        event.snapshot_id or "",
    )


def _string_path(path: str | Path | None) -> str | None:
    return str(path) if path is not None else None


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_replay_inputs_summary.json"
    md_path = root / "latest_replay_inputs_summary.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 28 Replay Inputs",
        "",
        "Research-only replay input normalization report. No execution authority.",
        "",
        f"Status: {payload['status']}",
        f"Events: {payload['event_count']}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Event Counts",
    ]
    lines.extend(f"- {name}: {count}" for name, count in payload["event_counts"].items())
    lines.extend(["", "## Limitations"])
    lines.extend(f"- {item}" for item in payload["limitations"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
