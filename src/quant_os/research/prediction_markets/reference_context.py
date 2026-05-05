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
