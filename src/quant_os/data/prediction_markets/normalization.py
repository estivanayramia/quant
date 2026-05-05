from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from quant_os.data.prediction_markets.schema import (
    MarketLifecycleStatus,
    PredictionMarketOutcome,
    PredictionMarketRecord,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
SCHEMA_VERSION = "1.0"


def load_prediction_market_payload(path: str | Path) -> dict[str, Any]:
    payload_path = Path(path)
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = "prediction market fixture must contain a JSON object"
        raise ValueError(msg)
    return payload


def load_prediction_market_records(path: str | Path) -> list[PredictionMarketRecord]:
    payload_path = Path(path)
    payload = load_prediction_market_payload(payload_path)
    return normalize_polymarket_payload(payload, source_path=payload_path)


def normalize_polymarket_payload(
    payload: dict[str, Any],
    *,
    source_path: str | Path | None = None,
) -> list[PredictionMarketRecord]:
    source_path_obj = Path(source_path) if source_path is not None else None
    source_mode = str(payload.get("source_mode") or _source_mode(source_path_obj))
    captured_at = _parse_time(payload.get("captured_at"))
    markets = payload.get("markets") or payload.get("data") or []
    if not isinstance(markets, list):
        msg = "prediction market payload must expose a markets list"
        raise ValueError(msg)

    records = [
        _normalize_market(
            raw,
            captured_at=captured_at,
            source_mode=source_mode,
            source_path=source_path_obj,
        )
        for raw in markets
        if isinstance(raw, dict)
    ]
    return sorted(records, key=lambda record: record.market_id)


def serialize_prediction_market_records(
    records: list[PredictionMarketRecord],
) -> list[dict[str, Any]]:
    return [record.model_dump(mode="json") | {"join_keys": record.join_keys} for record in records]


def _normalize_market(
    raw: dict[str, Any],
    *,
    captured_at: datetime | None,
    source_mode: str,
    source_path: Path | None,
) -> PredictionMarketRecord:
    market_id = str(raw.get("id") or raw.get("market_id") or raw.get("slug") or "unknown").strip()
    question = _clean_text(raw.get("question") or raw.get("title"))
    outcomes = _normalize_outcomes(raw)
    winner = _clean_text(
        raw.get("winner") or raw.get("winningOutcome") or raw.get("resolvedOutcome")
    )
    normalized_outcomes = [
        PredictionMarketOutcome(
            outcome_id=f"{market_id}:{index + 1}",
            name=name,
            contract_name=_contract_name(name, index),
            probability=price,
            price=price,
            winning=_is_winner(name, price, winner, bool(raw.get("resolved"))),
            source_outcome_id=_source_outcome_id(raw, index),
        )
        for index, (name, price) in enumerate(outcomes)
    ]
    return PredictionMarketRecord(
        schema_version=SCHEMA_VERSION,
        source="polymarket",
        source_mode=source_mode,
        market_id=market_id,
        condition_id=_optional_text(raw.get("conditionId") or raw.get("condition_id")),
        slug=_optional_text(raw.get("slug")),
        title=question,
        question=question,
        description=_optional_text(raw.get("description")),
        status=_lifecycle_status(raw),
        outcomes=normalized_outcomes,
        end_time=_parse_time(raw.get("endDate") or raw.get("end_date") or raw.get("endTime")),
        resolution_time=_parse_time(raw.get("resolutionTime") or raw.get("resolution_time")),
        volume=_optional_float(raw.get("volume") or raw.get("volumeNum")),
        liquidity=_optional_float(raw.get("liquidity") or raw.get("liquidityNum")),
        open_interest=_optional_float(raw.get("openInterest") or raw.get("open_interest")),
        category=_optional_text(raw.get("category")),
        tags=_normalize_tags(raw.get("tags")),
        event_id=_optional_text(raw.get("eventId") or raw.get("event_id")),
        captured_at=captured_at,
        updated_at=_parse_time(raw.get("updatedAt") or raw.get("updated_at")),
        source_url=_optional_text(raw.get("url") or raw.get("source_url")),
        provenance=_provenance(source_path),
        raw=raw,
    )


def _normalize_outcomes(raw: dict[str, Any]) -> list[tuple[str, float | None]]:
    names = _parse_list(raw.get("outcomes") or raw.get("outcomeNames"))
    prices = _parse_list(raw.get("outcomePrices") or raw.get("prices"))
    normalized: list[tuple[str, float | None]] = []
    for index, name in enumerate(names):
        text = _clean_text(name)
        if not text:
            continue
        normalized.append((text, _optional_float(prices[index] if index < len(prices) else None)))
    return normalized


def _parse_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        try:
            loaded = json.loads(stripped)
        except json.JSONDecodeError:
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return loaded if isinstance(loaded, list) else [loaded]
    return [value]


def _normalize_tags(value: Any) -> list[str]:
    tags = []
    for item in _parse_list(value):
        if isinstance(item, dict):
            item = item.get("label") or item.get("name") or item.get("slug")
        text = _clean_text(item)
        if text:
            tags.append(text)
    return sorted(set(tags))


def _lifecycle_status(raw: dict[str, Any]) -> MarketLifecycleStatus:
    resolution_status = str(raw.get("resolutionStatus") or "").lower()
    if bool(raw.get("disputed")) or resolution_status in {"disputed", "ambiguous"}:
        return MarketLifecycleStatus.DISPUTED
    if bool(raw.get("resolved")) or resolution_status == "resolved":
        return MarketLifecycleStatus.RESOLVED
    if bool(raw.get("closed")):
        return MarketLifecycleStatus.CLOSED
    if bool(raw.get("active")):
        return MarketLifecycleStatus.OPEN
    return MarketLifecycleStatus.AMBIGUOUS


def _contract_name(name: str, index: int) -> str:
    lowered = name.strip().lower()
    if lowered in {"yes", "y"}:
        return "YES"
    if lowered in {"no", "n"}:
        return "NO"
    normalized = re.sub(r"[^A-Z0-9]+", "_", name.upper()).strip("_")
    return normalized or f"OUTCOME_{index + 1}"


def _is_winner(name: str, price: float | None, winner: str, resolved: bool) -> bool | None:
    if not resolved:
        return None
    if winner:
        return name.strip().lower() == winner.strip().lower()
    if price is None:
        return None
    return price >= 0.999


def _source_outcome_id(raw: dict[str, Any], index: int) -> str | None:
    token_ids = _parse_list(raw.get("clobTokenIds") or raw.get("tokenIds"))
    if index < len(token_ids):
        return str(token_ids[index])
    tokens = _parse_list(raw.get("tokens"))
    if index < len(tokens) and isinstance(tokens[index], dict):
        token_id = tokens[index].get("token_id") or tokens[index].get("id")
        return str(token_id) if token_id else None
    return None


def _parse_time(value: Any) -> datetime | None:
    if value in {None, ""}:
        return None
    timestamp = pd.Timestamp(value)
    if pd.isna(timestamp):
        return None
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    return timestamp.tz_convert("UTC").to_pydatetime()


def _optional_float(value: Any) -> float | None:
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _optional_text(value: Any) -> str | None:
    text = _clean_text(value)
    return text or None


def _source_mode(path: Path | None) -> str:
    if path is None:
        return "memory"
    normalized = str(path).replace("\\", "/")
    return "fixture" if "tests/fixtures" in normalized else "cached_real"


def _provenance(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"source_path": None, "source_sha256": None}
    return {
        "source_path": str(path),
        "source_sha256": _sha256(path) if path.exists() else None,
        "normalized_at": datetime.now(UTC).isoformat(),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
