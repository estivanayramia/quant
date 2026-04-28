from __future__ import annotations

from quant_os.adapters.event_store_jsonl import JsonlEventStore
from quant_os.core.events import EventType, make_event
from quant_os.integrations.freqtrade.artifact_scanner import scan_freqtrade_artifacts
from quant_os.integrations.freqtrade.trade_normalizer import (
    ingest_trade_artifacts,
    normalize_trade_artifacts,
)
from quant_os.integrations.freqtrade.trade_reconciliation import reconcile_freqtrade_trades
from quant_os.integrations.freqtrade.trade_reporting import write_freqtrade_trade_report


def freqtrade_trade_artifact_status(
    event_store: JsonlEventStore | None = None,
) -> dict[str, object]:
    scan = scan_freqtrade_artifacts()
    ingestion = ingest_trade_artifacts()
    normalized = normalize_trade_artifacts(ingestion.get("parsed_artifacts", []))
    reconciliation = reconcile_freqtrade_trades(normalized.get("records", []))
    write_freqtrade_trade_report()
    payload = {
        "freqtrade_trade_artifacts": {
            "artifact_scan_status": scan["status"],
            "artifacts_found": scan["artifacts_found"],
            "parsed_records": ingestion["parsed_records_count"],
            "normalized_records": normalized["normalized_records_count"],
            "trade_reconciliation_status": reconciliation["status"],
            "trade_level_comparison_available": reconciliation["trade_level_comparison_available"],
            "blockers": reconciliation["failures"],
            "warnings": reconciliation["warnings"],
            "latest_report_path": "reports/freqtrade/trades/latest_trade_report.md",
            "live_promotion_status": "TINY_LIVE_BLOCKED",
            "autonomous_start_allowed": False,
        }
    }
    if event_store is not None:
        event_store.append(
            make_event(EventType.REPORT_GENERATED, "freqtrade-trade-artifacts", payload)
        )
    return payload
