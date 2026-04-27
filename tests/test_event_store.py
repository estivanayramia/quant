from __future__ import annotations

from quant_os.core.events import EventType, make_event


def test_event_store_appends_events(event_store):
    event_store.append(make_event(EventType.DATA_SEEDED, "demo", {"rows": 1}))
    events = event_store.read_all()
    assert len(events) == 1
    assert events[0].event_type == EventType.DATA_SEEDED
