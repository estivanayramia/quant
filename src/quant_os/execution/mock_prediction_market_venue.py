from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MockPredictionMarketVenue:
    orders: dict[str, dict[str, Any]] = field(default_factory=dict)
    actual_order_count: int = 0
    actual_cancel_count: int = 0
    authenticated_endpoint_called: bool = False
    request_signing_enabled: bool = False
    api_keys_loaded: bool = False
    private_keys_loaded: bool = False

    def submit_order(self, intent: dict[str, Any], *, scenario: str = "accept") -> dict[str, Any]:
        client_id = str(intent.get("client_order_id_preview") or intent.get("fake_client_order_id") or "")
        if not client_id:
            return self._event("MOCK_REJECTED", scenario, intent, reason_code="MISSING_CLIENT_ORDER_ID")
        if client_id in self.orders and scenario != "idempotency_replay":
            return self._event("MOCK_REJECTED", scenario, intent, reason_code="DUPLICATE_CLIENT_ORDER_ID")
        if scenario == "idempotency_replay" and client_id in self.orders:
            return {**self.orders[client_id], "idempotency_replayed": True}
        if scenario in {"market_closed", "stale_price", "reject", "unknown_order"}:
            reason = {
                "market_closed": "MARKET_CLOSED",
                "stale_price": "STALE_PRICE",
                "reject": "MOCK_PRE_SUBMIT_REJECT",
                "unknown_order": "UNKNOWN_ORDER",
            }[scenario]
            return self._event("MOCK_REJECTED", scenario, intent, reason_code=reason)
        if scenario in {"no_fill", "price_moved_no_fill"}:
            event = self._event("MOCK_NO_FILL", scenario, intent, reason_code="PRICE_MOVED_NO_FILL")
        elif scenario == "partial_fill":
            event = self._event("MOCK_PARTIAL_FILL", scenario, intent, filled_contracts=1)
        elif scenario == "full_fill":
            event = self._event(
                "MOCK_FULL_FILL",
                scenario,
                intent,
                filled_contracts=int(intent.get("max_contracts") or 1),
            )
        elif scenario == "timeout":
            event = self._event("MOCK_TIMEOUT", scenario, intent, reason_code="MOCK_VENUE_TIMEOUT")
        else:
            event = self._event("MOCK_ACCEPTED", scenario, intent, filled_contracts=0)
        self.orders[client_id] = event
        return event

    def request_cancel(self, client_id: str, *, scenario: str = "cancel_accepted") -> dict[str, Any]:
        if client_id not in self.orders:
            return {
                "status": "MOCK_REJECTED",
                "scenario": "unknown_order_rejected",
                "reason_code": "UNKNOWN_ORDER",
                "actual_cancel_count": 0,
            }
        if scenario == "cancel_rejected":
            return {
                "status": "MOCK_CANCEL_REJECTED",
                "scenario": scenario,
                "client_order_id_preview": client_id,
                "reason_code": "ALREADY_FILLED_OR_UNKNOWN",
                "actual_cancel_count": 0,
            }
        return {
            "status": "MOCK_CANCEL_ACCEPTED",
            "scenario": scenario,
            "client_order_id_preview": client_id,
            "reason_code": "FAKE_CANCEL_ACCEPTED",
            "actual_cancel_count": 0,
        }

    def _event(
        self,
        status: str,
        scenario: str,
        intent: dict[str, Any],
        *,
        reason_code: str | None = None,
        filled_contracts: int = 0,
    ) -> dict[str, Any]:
        client_id = str(intent.get("client_order_id_preview") or intent.get("fake_client_order_id"))
        event = {
            "status": status,
            "scenario": scenario,
            "mock_order_id": _hash({"client_id": client_id, "scenario": scenario}),
            "client_order_id_preview": client_id,
            "market_ticker": intent.get("market_ticker"),
            "limit_price": intent.get("limit_price"),
            "filled_contracts": filled_contracts,
            "fill_price": intent.get("limit_price") if filled_contracts else None,
            "reason_code": reason_code or status,
            "fake_money": True,
            "dry_run_only": True,
            "no_send": True,
            "authenticated_endpoint_called": False,
            "actual_order_count": 0,
        }
        return event


def _hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str)
    return f"mock_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"
