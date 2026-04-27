from __future__ import annotations

from quant_os.core.events import DomainEvent, EventType
from quant_os.domain.fills import Fill
from quant_os.domain.portfolio import PortfolioState


def rebuild_portfolio_from_events(events: list[DomainEvent]) -> PortfolioState:
    portfolio = PortfolioState()
    for event in events:
        if event.event_type == EventType.ORDER_FILLED:
            fill_payload = event.payload.get("fill")
            if isinstance(fill_payload, dict):
                portfolio.apply_fill(Fill.model_validate(fill_payload))
    return portfolio
