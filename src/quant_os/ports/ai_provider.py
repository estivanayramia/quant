from __future__ import annotations

from typing import Protocol


class AIProviderPort(Protocol):
    def critique_strategy(self, strategy_id: str, metrics: dict[str, object]) -> str: ...

    def daily_report_summary(self, context: dict[str, object]) -> str: ...

    def risk_notes(self, risk_context: dict[str, object]) -> str: ...
