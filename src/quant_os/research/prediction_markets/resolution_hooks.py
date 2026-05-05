from __future__ import annotations

from typing import Any

from quant_os.data.prediction_markets.schema import (
    MarketLifecycleStatus,
    PredictionMarketRecord,
)


def build_resolution_label_hooks(records: list[PredictionMarketRecord]) -> list[dict[str, Any]]:
    hooks = []
    for record in records:
        winning = next((outcome for outcome in record.outcomes if outcome.winning is True), None)
        hooks.append(
            {
                "schema_version": "1.0",
                "source": record.source,
                "source_mode": record.source_mode,
                "market_id": record.market_id,
                "condition_id": record.condition_id,
                "resolution_status": record.status.value,
                "winning_outcome": winning.contract_name if winning else None,
                "label_ready": bool(record.status == MarketLifecycleStatus.RESOLVED and winning),
                "resolution_time": record.resolution_time.isoformat()
                if record.resolution_time
                else None,
                "join_keys": record.join_keys,
                "internet_required": False,
                "label_use": "future_research_join_only",
            }
        )
    return hooks
