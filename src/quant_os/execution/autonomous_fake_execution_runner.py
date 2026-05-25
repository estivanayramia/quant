from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.execution.mock_prediction_market_venue import MockPredictionMarketVenue
from quant_os.readiness.canary_readiness_common import (
    load_gate_payload,
    safety_payload,
    write_json_markdown_report,
)

REPORT_DIR = Path("reports/autonomous_live_fire_drill/fake_execution")


def run_fake_execution(
    *,
    output_root: str | Path = ".",
    intent_payload: dict[str, Any] | None = None,
    scenario: str = "full_fill",
) -> dict[str, Any]:
    intent_payload = intent_payload or load_gate_payload(
        "reports/autonomous_live_fire_drill/no_transmit_intent/latest_intent.json",
        output_root=output_root,
    ) or {}
    intent = intent_payload.get("intent")
    if not intent:
        return safety_payload(
            schema_version="autonomous_fake_execution_v1",
            status="FAKE_EXECUTION_NO_TRADE",
            allowed_statuses=[
                "FAKE_EXECUTION_RUNNER_READY",
                "FAKE_EXECUTION_PASSED",
                "FAKE_EXECUTION_NO_TRADE",
                "FAKE_EXECUTION_FAILED",
            ],
            fake_order_state="NO_TRADE",
            fake_position_state="NO_POSITION",
            fake_pnl={"realized_pnl": 0.0, "mark_to_market_pnl": 0.0},
            venue_event=None,
            actual_order_count=0,
            actual_cancel_count=0,
            authenticated_endpoint_called=False,
            request_signing_enabled=False,
            api_keys_loaded=False,
            private_keys_loaded=False,
            blockers=[],
            next_action="Run risk and reconciliation on no-trade state.",
        )
    venue = MockPredictionMarketVenue()
    event = venue.submit_order(intent, scenario=scenario)
    filled = int(event.get("filled_contracts") or 0)
    pnl = {
        "realized_pnl": 0.0,
        "mark_to_market_pnl": round(-float(event.get("fill_price") or 0.0) * filled, 6),
    }
    return safety_payload(
        schema_version="autonomous_fake_execution_v1",
        status="FAKE_EXECUTION_PASSED" if event.get("status") != "MOCK_REJECTED" else "FAKE_EXECUTION_FAILED",
        allowed_statuses=[
            "FAKE_EXECUTION_RUNNER_READY",
            "FAKE_EXECUTION_PASSED",
            "FAKE_EXECUTION_NO_TRADE",
            "FAKE_EXECUTION_FAILED",
        ],
        fake_order_state=event["status"],
        fake_position_state="OPEN_FAKE_POSITION" if filled else "NO_POSITION",
        fake_positions=[{"market_ticker": intent.get("market_ticker"), "contracts": filled}],
        fake_pnl=pnl,
        venue_event=event,
        actual_order_count=0,
        actual_cancel_count=0,
        authenticated_endpoint_called=False,
        request_signing_enabled=False,
        api_keys_loaded=False,
        private_keys_loaded=False,
        blockers=[] if event.get("status") != "MOCK_REJECTED" else [event.get("reason_code")],
        next_action="Run risk and fake reconciliation.",
    )


def write_fake_execution_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = run_fake_execution(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_fake_execution.json",
        md_name="latest_fake_execution.md",
        title="Autonomous Fake Execution",
        summary="Fake-money execution runner against local mock venue only.",
    )
    return payload
