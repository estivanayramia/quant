from __future__ import annotations

from quant_os.core.events import DomainEvent


def event_type_counts(events: list[DomainEvent]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        counts[str(event.event_type)] = counts.get(str(event.event_type), 0) + 1
    return counts
