from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Any

from quant_os.data.prediction_markets.schema import (
    MarketLifecycleStatus,
    PredictionMarketRecord,
)

RESEARCHABLE = "RESEARCHABLE"
LOW_PRIORITY = "LOW_PRIORITY"
DO_NOT_RESEARCH_YET = "DO_NOT_RESEARCH_YET"
AMBIGUOUS_MARKET_STRUCTURE = "AMBIGUOUS_MARKET_STRUCTURE"

DEFAULT_QUALITY_POLICY = {
    "max_staleness_days": 14.0,
    "min_liquidity_usd": 1_000.0,
    "min_volume_usd": 5_000.0,
}


def evaluate_market_quality(
    records: list[PredictionMarketRecord],
    *,
    as_of: datetime | None = None,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    effective_policy = DEFAULT_QUALITY_POLICY | (policy or {})
    evaluation_time = as_of or datetime.now(UTC)
    markets = [
        score_market_quality(record, as_of=evaluation_time, policy=effective_policy)
        for record in records
    ]
    status_counts = Counter(item["research_worthiness"] for item in markets)
    return {
        "generated_at": evaluation_time.isoformat(),
        "sequence": "20",
        "source": "polymarket",
        "source_mode": _source_mode(records),
        "market_count": len(records),
        "summary": {
            "researchable_count": int(status_counts[RESEARCHABLE]),
            "low_priority_count": int(status_counts[LOW_PRIORITY]),
            "do_not_research_yet_count": int(status_counts[DO_NOT_RESEARCH_YET]),
            "ambiguous_market_structure_count": int(status_counts[AMBIGUOUS_MARKET_STRUCTURE]),
        },
        "markets": markets,
        "policy": effective_policy,
        "observed_facts": [
            "Quality scores are computed only from saved market metadata.",
            "Volume, liquidity, status, outcome count, and timestamp fields are observed inputs.",
        ],
        "inferred_patterns": [
            "Research worthiness is a screening heuristic, not a profitability claim.",
        ],
        "unknowns": [
            "Resolution quality, wallet causality, and venue-specific fill realism remain unproven.",
        ],
        "live_trading_enabled": False,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def score_market_quality(
    record: PredictionMarketRecord,
    *,
    as_of: datetime,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    effective_policy = DEFAULT_QUALITY_POLICY | (policy or {})
    flags = _critical_flags(record)
    flags.extend(_structure_flags(record))
    flags.extend(_quality_flags(record, as_of=as_of, policy=effective_policy))
    flags = sorted(set(flags))
    return {
        "market_id": record.market_id,
        "condition_id": record.condition_id,
        "slug": record.slug,
        "title": record.title,
        "status": record.status.value,
        "outcome_count": len(record.outcomes),
        "volume": record.volume,
        "liquidity": record.liquidity,
        "open_interest": record.open_interest,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        "end_time": record.end_time.isoformat() if record.end_time else None,
        "quality_flags": flags,
        "research_worthiness": _worthiness(flags),
        "source_mode": record.source_mode,
        "join_keys": record.join_keys,
    }


def _critical_flags(record: PredictionMarketRecord) -> list[str]:
    flags: list[str] = []
    if not record.market_id or record.market_id == "unknown":
        flags.append("MISSING_MARKET_ID")
    if not record.condition_id:
        flags.append("MISSING_CONDITION_ID")
    if not record.question:
        flags.append("MISSING_QUESTION")
    if not record.outcomes:
        flags.append("MISSING_OUTCOMES")
    if record.status != MarketLifecycleStatus.RESOLVED and record.end_time is None:
        flags.append("MISSING_END_TIME")
    return flags


def _structure_flags(record: PredictionMarketRecord) -> list[str]:
    if not record.outcomes:
        return []
    contract_names = {outcome.contract_name for outcome in record.outcomes}
    if len(record.outcomes) != 2 or contract_names != {"YES", "NO"}:
        return ["NON_BINARY_OUTCOMES"]
    return []


def _quality_flags(
    record: PredictionMarketRecord,
    *,
    as_of: datetime,
    policy: dict[str, Any],
) -> list[str]:
    flags: list[str] = []
    if record.status == MarketLifecycleStatus.RESOLVED:
        flags.append("RESOLVED_MARKET")
    timestamp = record.updated_at or record.captured_at
    if timestamp is None:
        flags.append("MISSING_FRESHNESS_TIMESTAMP")
    else:
        age_days = abs((as_of - timestamp).total_seconds()) / 86_400.0
        if age_days > float(policy["max_staleness_days"]):
            flags.append("STALE_MARKET")
    if record.liquidity is None:
        flags.append("MISSING_LIQUIDITY")
    elif record.liquidity < float(policy["min_liquidity_usd"]):
        flags.append("THIN_LIQUIDITY")
    if record.volume is None:
        flags.append("MISSING_VOLUME")
    elif record.volume < float(policy["min_volume_usd"]):
        flags.append("LOW_VOLUME")
    return flags


def _worthiness(flags: list[str]) -> str:
    critical = {
        "MISSING_MARKET_ID",
        "MISSING_CONDITION_ID",
        "MISSING_QUESTION",
        "MISSING_OUTCOMES",
        "MISSING_END_TIME",
    }
    if critical.intersection(flags):
        return DO_NOT_RESEARCH_YET
    if "NON_BINARY_OUTCOMES" in flags:
        return AMBIGUOUS_MARKET_STRUCTURE
    if flags:
        return LOW_PRIORITY
    return RESEARCHABLE


def _source_mode(records: list[PredictionMarketRecord]) -> str:
    modes = sorted({record.source_mode for record in records})
    return modes[0] if len(modes) == 1 else "mixed"
