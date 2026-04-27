from __future__ import annotations

from quant_os.core.events import EventType, make_event
from quant_os.domain.fills import Fill
from quant_os.domain.portfolio import PortfolioState
from quant_os.domain.positions import Position
from quant_os.ports.event_store import EventStorePort


class PMS:
    def __init__(
        self, event_store: EventStorePort, portfolio: PortfolioState | None = None
    ) -> None:
        self.event_store = event_store
        self.portfolio = portfolio or PortfolioState()

    def apply_fill(self, fill: Fill) -> Position:
        was_open = fill.symbol in self.portfolio.positions
        position = self.portfolio.apply_fill(fill)
        if position.is_open and not was_open:
            event_type = EventType.POSITION_OPENED
        elif position.is_open:
            event_type = EventType.POSITION_UPDATED
        else:
            event_type = EventType.POSITION_CLOSED
        self.event_store.append(
            make_event(
                event_type,
                fill.symbol,
                {"position": position.model_dump(mode="json"), "fill_id": fill.fill_id},
            )
        )
        return position
