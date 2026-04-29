from __future__ import annotations

from typing import Any

from quant_os.adapters.event_store_jsonl import JsonlEventStore
from quant_os.autonomy.supervisor import Supervisor
from quant_os.core.events import EventType, make_event
from quant_os.projections.incident_projection import rebuild_incident_projection
from quant_os.projections.proving_projection import rebuild_proving_projection
from quant_os.proving.incident_log import append_incidents, incidents_for_record, load_incidents
from quant_os.proving.proving_report import write_proving_report
from quant_os.proving.readiness import evaluate_proving_readiness
from quant_os.proving.run_history import append_proving_record, load_proving_history
from quant_os.proving.run_record import build_proving_record


def run_proving_once(event_store: JsonlEventStore | None = None) -> dict[str, Any]:
    event_store = event_store or JsonlEventStore()
    state = Supervisor().run_once()
    record = build_proving_record(state)
    incidents = incidents_for_record(record.model_dump(mode="json"))
    record.incidents_created = [item["incident_id"] for item in incidents]
    status = append_proving_record(record)
    incident_summary = append_incidents(incidents)
    history = load_proving_history()
    readiness = evaluate_proving_readiness(history)
    report = write_proving_report()
    rebuild_proving_projection(history)
    rebuild_incident_projection(load_incidents())
    event_store.append(
        make_event(
            EventType.PROVING_RUN_RECORDED,
            record.run_id,
            {
                "record": record.model_dump(mode="json"),
                "readiness": readiness["readiness_status"],
                "incidents_created": record.incidents_created,
            },
        )
    )
    return {
        "record": record.model_dump(mode="json"),
        "status": status,
        "incident_summary": incident_summary,
        "readiness": readiness,
        "report": report,
    }
