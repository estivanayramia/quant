from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from quant_os.live_canary.exchange_port import LiveCanaryExchangePort


def build_balance_snapshot(adapter: LiveCanaryExchangePort) -> dict[str, Any]:
    capabilities = adapter.capabilities()
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "adapter_available": capabilities.adapter_available,
        "exchange_name": capabilities.exchange_name,
        "balances": [],
        "positions": [position.__dict__ for position in adapter.get_open_positions()]
        if capabilities.adapter_available
        else [],
        "secrets_present": False,
        "live_promotion_status": "LIVE_BLOCKED",
    }
