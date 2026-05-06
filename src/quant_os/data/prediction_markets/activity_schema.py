from __future__ import annotations

ACTIVITY_EVENT_TYPES = {
    "trade",
    "quote_snapshot",
    "order_book_snapshot",
    "liquidity_update",
    "market_lifecycle_update",
    "resolution_update",
}

TRADE_LIKE_EVENT_TYPES = {"trade"}
QUOTE_LIKE_EVENT_TYPES = {"quote_snapshot", "order_book_snapshot"}

CRITICAL_EVENT_FIELDS = ("event_id", "market_id", "timestamp", "event_type", "price")
