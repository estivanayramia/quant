from __future__ import annotations

import hashlib
import uuid
from datetime import datetime


def deterministic_id(namespace: str, *parts: object, length: int = 16) -> str:
    raw = "|".join([namespace, *(str(part) for part in parts)])
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"{namespace}_{digest[:length]}"


def deterministic_client_order_id(
    strategy_id: str,
    symbol: str,
    side: str,
    created_at: datetime,
    sequence: int,
) -> str:
    return deterministic_id("co", strategy_id, symbol, side, created_at.isoformat(), sequence)


def new_event_id() -> str:
    return f"evt_{uuid.uuid4().hex}"


def new_fill_id(client_order_id: str, sequence: int) -> str:
    return deterministic_id("fill", client_order_id, sequence)
