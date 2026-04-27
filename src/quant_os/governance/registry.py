from __future__ import annotations

from quant_os.core.events import EventType, make_event
from quant_os.domain.quarantine import StrategyQuarantineState
from quant_os.domain.strategy import StrategyRecord, StrategyStatus
from quant_os.ports.event_store import EventStorePort


class StrategyRegistry:
    def __init__(self, event_store: EventStorePort | None = None) -> None:
        self.event_store = event_store
        self.records: dict[str, StrategyRecord] = {}
        self.quarantine_state = StrategyQuarantineState()

    def register(self, record: StrategyRecord) -> None:
        self.records[record.strategy_id] = record

    def quarantine(self, strategy_id: str, reason: str) -> None:
        self.quarantine_state.quarantine(strategy_id, reason)
        if strategy_id in self.records:
            self.records[strategy_id].quarantined = True
            self.records[strategy_id].status = StrategyStatus.QUARANTINED
        if self.event_store is not None:
            self.event_store.append(
                make_event(
                    EventType.STRATEGY_QUARANTINED,
                    strategy_id,
                    {"strategy_id": strategy_id, "reason": reason},
                )
            )

    def release(self, strategy_id: str) -> None:
        self.quarantine_state.release(strategy_id)
        if strategy_id in self.records:
            self.records[strategy_id].quarantined = False
            self.records[strategy_id].status = StrategyStatus.RESEARCH
        if self.event_store is not None:
            self.event_store.append(
                make_event(EventType.STRATEGY_RELEASED, strategy_id, {"strategy_id": strategy_id})
            )

    def is_quarantined(self, strategy_id: str) -> bool:
        return self.quarantine_state.is_quarantined(strategy_id)

    def transition(self, strategy_id: str, status: StrategyStatus) -> None:
        if status in {StrategyStatus.PAPER, StrategyStatus.CANARY_CANDIDATE}:
            msg = "paper/canary promotion is future-gated and disabled in Milestone 2"
            raise RuntimeError(msg)
        self.records[strategy_id].status = status
