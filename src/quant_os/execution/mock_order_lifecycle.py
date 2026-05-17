from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.execution.mock_prediction_market_venue import MockPredictionMarketVenue
from quant_os.readiness.canary_readiness_common import safety_payload, write_json_markdown_report

REPORT_DIR = Path("reports/autonomous_live_fire_drill/mock_lifecycle")


def build_mock_order_lifecycle(*, output_root: str | Path = ".") -> dict[str, Any]:
    venue = MockPredictionMarketVenue()
    intent = _intent("fd_lifecycle_1")
    events = [
        venue.submit_order(intent, scenario="accepted"),
        venue.submit_order(_intent("fd_lifecycle_2"), scenario="reject") | {"scenario": "rejected"},
        venue.submit_order(_intent("fd_lifecycle_3", max_contracts=2), scenario="partial_fill"),
        venue.submit_order(_intent("fd_lifecycle_4"), scenario="full_fill"),
        venue.submit_order(_intent("fd_lifecycle_5"), scenario="no_fill"),
        venue.submit_order(_intent("fd_lifecycle_6"), scenario="timeout"),
        venue.request_cancel("fd_lifecycle_1", scenario="cancel_accepted"),
        venue.request_cancel("fd_lifecycle_4", scenario="cancel_rejected"),
        venue.submit_order(intent, scenario="accepted") | {"scenario": "duplicate_rejected"},
        venue.submit_order(_intent("fd_lifecycle_7"), scenario="market_closed")
        | {"scenario": "market_closed_rejected"},
        venue.submit_order(_intent("fd_lifecycle_8"), scenario="stale_price")
        | {"scenario": "stale_price_rejected"},
        venue.submit_order(_intent("fd_lifecycle_9"), scenario="price_moved_no_fill"),
        venue.request_cancel("fd_unknown", scenario="unknown_order_rejected"),
        venue.submit_order(intent, scenario="idempotency_replay") | {"scenario": "idempotency_replay"},
    ]
    required_ok = all(event.get("actual_order_count", 0) == 0 for event in events)
    status = "MOCK_ORDER_LIFECYCLE_PASSED" if required_ok else "MOCK_ORDER_LIFECYCLE_FAILED"
    return safety_payload(
        schema_version="mock_order_lifecycle_v1",
        status=status,
        allowed_statuses=[
            "MOCK_ORDER_LIFECYCLE_READY",
            "MOCK_ORDER_LIFECYCLE_PASSED",
            "MOCK_ORDER_LIFECYCLE_FAILED",
        ],
        events=events,
        mock_accepted_count=sum(1 for event in events if event.get("status") == "MOCK_ACCEPTED"),
        mock_rejected_count=sum(1 for event in events if event.get("status") == "MOCK_REJECTED"),
        fake_fills_count=sum(
            1 for event in events if event.get("status") in {"MOCK_FULL_FILL", "MOCK_PARTIAL_FILL"}
        ),
        fake_no_fills_count=sum(1 for event in events if event.get("status") == "MOCK_NO_FILL"),
        fake_cancels_timeouts_count=sum(
            1
            for event in events
            if event.get("status") in {"MOCK_CANCEL_ACCEPTED", "MOCK_TIMEOUT"}
        ),
        authenticated_endpoint_called=False,
        request_signing_enabled=False,
        api_keys_loaded=False,
        private_keys_loaded=False,
        blockers=[] if required_ok else ["MOCK_VENUE_USED_REAL_COUNT"],
        next_action="Run fake execution runner.",
    )


def write_mock_order_lifecycle_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_mock_order_lifecycle(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_mock_lifecycle.json",
        md_name="latest_mock_lifecycle.md",
        title="Mock Order Lifecycle",
        summary="Local-only mock venue lifecycle. No real auth, endpoints, orders, cancels, or signing.",
    )
    return payload


def _intent(client_id: str, *, max_contracts: int = 1) -> dict[str, Any]:
    return {
        "client_order_id_preview": client_id,
        "market_ticker": "KXHIGHNY-26MAY18-B83.5",
        "limit_price": 0.27,
        "max_contracts": max_contracts,
        "max_nominal_exposure": 1.0,
        "fake_money": True,
        "dry_run_only": True,
        "no_send": True,
    }
