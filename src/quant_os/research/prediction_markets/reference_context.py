from __future__ import annotations

from typing import Any

from quant_os.data.prediction_markets.schema import (
    MarketLifecycleStatus,
    PredictionMarketRecord,
)


def build_reference_context_hooks(records: list[PredictionMarketRecord]) -> list[dict[str, Any]]:
    hooks = []
    for record in records:
        hooks.append(
            {
                "source": record.source,
                "source_mode": record.source_mode,
                "market_id": record.market_id,
                "condition_id": record.condition_id,
                "title": record.title,
                "event_time": record.end_time.isoformat() if record.end_time else None,
                "resolution_time": record.resolution_time.isoformat()
                if record.resolution_time
                else None,
                "reference_required": record.status != MarketLifecycleStatus.RESOLVED,
                "reference_status": "PLACEHOLDER_PENDING",
                "internet_required": False,
                "join_keys": record.join_keys,
                "unknowns": [
                    "External reference data is not attached in Phase 20.",
                    "Resolution semantics need later manual or validated offline labels.",
                ],
            }
        )
    return hooks


def attach_offline_reference_context(dataset: dict[str, Any]) -> list[dict[str, Any]]:
    references = []
    for market in dataset["markets"]:
        context = market.get("reference_context") or {}
        resolution = market.get("resolution") or {}
        references.append(
            {
                "source": "polymarket",
                "source_mode": dataset["source_mode"],
                "market_id": market["market_id"],
                "condition_id": market["condition_id"],
                "event_time": context.get("event_time"),
                "resolution_criteria": context.get("resolution_criteria"),
                "reference_label": context.get("reference_label"),
                "reference_status": "ATTACHED_OFFLINE" if context else "MISSING_REFERENCE_CONTEXT",
                "observed_market_data": bool(market.get("snapshots")),
                "attached_resolution_truth": resolution.get("status") == "RESOLVED",
                "internet_required": False,
                "join_keys": {
                    "source": "polymarket",
                    "market_id": market["market_id"],
                    "condition_id": market["condition_id"],
                },
                "unknowns": [
                    "Reference context comes from offline fixtures and is not refreshed in CI.",
                    "Unresolved or ambiguous markets must not be used as resolved training labels.",
                ],
            }
        )
    return references
