from __future__ import annotations

from pydantic import BaseModel


class NoTradeDecision(BaseModel):
    blocked: bool = False
    reasons: list[str] = []


class NoTradeEngine:
    def evaluate(
        self, explicit_flag: bool = False, reasons: list[str] | None = None
    ) -> NoTradeDecision:
        merged = list(reasons or [])
        if explicit_flag:
            merged.append("NO_TRADE_FLAG")
        return NoTradeDecision(blocked=bool(merged), reasons=merged)
