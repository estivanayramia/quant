from __future__ import annotations

from quant_os.adapters.event_store_jsonl import JsonlEventStore
from quant_os.core.events import EventType, make_event
from quant_os.monitoring.monitoring_report import generate_dryrun_monitoring_report


def dryrun_monitoring_status(event_store: JsonlEventStore | None = None) -> dict[str, object]:
    payload = generate_dryrun_monitoring_report()
    if event_store is not None:
        event_store.append(make_event(EventType.REPORT_GENERATED, "dryrun-monitoring", payload))
    return {
        "dryrun_monitoring": {
            "history_records_count": payload["history_records_count"],
            "latest_comparison_status": payload["latest_comparison_status"],
            "latest_divergence_status": payload["latest_divergence_status"],
            "latest_promotion_status": payload["latest_promotion_status"],
            "live_promotion_status": payload["live_promotion_status"],
            "blockers": payload["blockers"],
            "warnings": payload["warnings"],
            "latest_report_path": payload["latest_report_path"],
            "next_manual_commands": payload["next_manual_commands"],
            "autonomous_start_allowed": False,
        }
    }
