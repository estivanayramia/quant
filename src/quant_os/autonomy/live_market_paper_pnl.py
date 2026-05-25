from __future__ import annotations

from typing import Any


def calculate_fake_pnl(
    *,
    intent: dict[str, Any] | None,
    fake_fill: dict[str, Any] | None,
    mark_price: float | None = None,
) -> dict[str, float | str]:
    if not intent or not fake_fill:
        return {
            "state": "NO_POSITION",
            "mark_to_market_pnl": 0.0,
            "pending_settlement_pnl": 0.0,
            "realized_pnl": 0.0,
        }
    fill_price = float(fake_fill.get("fill_price") or 0.0)
    contracts = int(fake_fill.get("filled_contracts") or 0)
    mark = float(mark_price if mark_price is not None else fill_price)
    return {
        "state": "OPEN_FAKE_POSITION",
        "mark_to_market_pnl": round((mark - fill_price) * contracts, 6),
        "pending_settlement_pnl": 0.0,
        "realized_pnl": 0.0,
    }
