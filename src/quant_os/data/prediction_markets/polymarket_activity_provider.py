from __future__ import annotations

from typing import Any

POLYMARKET_ACTIVITY_PROVIDER_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
}


class PolymarketActivityProvider:
    """Read-only provider shell for explicit manual captures."""

    def __init__(self, http_client: Any | None = None) -> None:
        self._http_client = http_client

    def fetch_activity(
        self,
        *,
        lane_id: str,
        manual_network: bool,
        explicit_network_ack: bool,
    ) -> dict[str, Any]:
        if not manual_network:
            return _blocked("MANUAL_NETWORK_NOT_REQUESTED", lane_id=lane_id)
        if not explicit_network_ack:
            return _blocked("EXPLICIT_NETWORK_ACK_REQUIRED", lane_id=lane_id)
        if self._http_client is None:
            return _blocked("OPTIONAL_HTTP_CLIENT_UNAVAILABLE", lane_id=lane_id)
        return {
            "status": "BLOCKED",
            "reason": "NETWORK_CAPTURE_NOT_IMPLEMENTED_IN_CI_PATH",
            "lane_id": lane_id,
            "network_fetch_attempted": False,
            **POLYMARKET_ACTIVITY_PROVIDER_SAFETY,
        }


def _blocked(reason: str, *, lane_id: str) -> dict[str, Any]:
    return {
        "status": "BLOCKED",
        "reason": reason,
        "lane_id": lane_id,
        "network_fetch_attempted": False,
        **POLYMARKET_ACTIVITY_PROVIDER_SAFETY,
    }
